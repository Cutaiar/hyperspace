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
- ``render`` / ``output`` — the wired frame's nodes (plan 35 G): one per
  name the preset's section says, by an entry or a wire's end, in the
  owner's ids (``render:<id>``: ``render:scene``, ``render:hands.layer``,
  ``render:lookback``, ``render:acid.2``, ``render:copy`` …), titled in the
  owner's words (`label_of`, `LABELS`) and hovered by what each is
  (`hover_of`, `HOVERS`), their ports a wired frame's (`graph.WIRED_TAKES`,
  ``rin:lookback/capture``) and, as input ports, the params of the node
  that owns them (`OWNERS`, the one table); ``render:output.all`` and each
  window ``render:output.<n>`` always; ``render:camera`` — the shared
  camera (`camera.*`, `eye.*`), the rig's, which draws through every scene
  and so has no picture port; a cloud, the rig's; a node the section
  declares or wires that reaches nothing (`unreached`) ``faint``
  ("reaches nothing");
- ``channel`` — the eight media channels (``render:channel.<c>``, plan 32
  T10), always, each with its picture out and its `media.<c>.*` params;
  one with an empty bin and no cable sits on MEDIA's idle line;
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
wire of the section, `ref` its `graph.Wire` — plan 36 T1: or a bus cable
of the rig's, ``rout:output.all.<port>`` into a window's same port, `ref`
its `graph.bus_wire`, drawn while the open show has not cut it and the
section does not wire that port itself), ``lane`` (plan 31: a
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
the modifiers, the macros) → (plan 35 G: by primitive) *media* (the
eight channels, plan 32 T10; plan 33 the pattern, the switches, and any
effect or composite made of the media alone, `media_made`; plan 34's
delays) → *scene* (the shape, the hands, their layers and guides, a
cloud, the camera, the scene that draws them, the backdrop) →
*look-back* (the look-back, its echoes, the dream) → *effects* (the
effects, the copies, the composites, a resize) → *outputs* (All outputs,
then each window). Every wire runs right but the effects' wrapped rows,
a scene picture taken back into a switch, and what is kept for the next
frame — into `lookback.capture`, into a delay (`returns`). `AREA` is the one table (`area_of`);
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
from typing import Any

from . import envelope as envmod
from . import graph as rgraph
from . import graphmigrate, modbank
from . import learn as learnmod
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
         "render", "output", "template", "channel")
# plan 35 G: the kinds a wired frame's node is drawn as (its render-side ones)
FRAME_VKINDS = ("render", "output", "channel")
# plan 31 G1: ``lane`` is a sequencer lane's envelope binding (``seq.<l>.env``,
# a fixed link the sequencer fires directly — no row), drawn as a cable
CABLE_KINDS = ("route", "setter", "sub", "input", "render", "lane")
IN, OUT = "in", "out"
BASE, MOD, DEPTH = "base", "mod", "depth"
# which layout map a node's position is saved in
PRESET, SESSION = "preset", "session"

ANALYZER = "analyzer"
CAMERA = "camera"            # the shared camera's node: `render:camera` (plan 35 V2: was `eye`)
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
    # plan 35 V2: `ghost[.n].*` is hands node `hands[.n]`'s (params keep their ids)
    n = _first_segment_number(pid, "ghost")
    return rgraph.wired_hands_name(n)


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
    return None


def _output_owner(pid: str, ctx: _Ctx) -> str | None:
    seg = pid.split(".")
    if len(seg) >= 3 and seg[0] == "output" and seg[1].isdigit():
        return f"output.{seg[1]}"
    return None


def _cloud_owner(pid: str, ctx: _Ctx) -> str | None:
    return ctx.first_cloud


def _media_owner(pid: str, ctx: _Ctx) -> str | None:
    # plan 32 T10: `media.<c>.<key>` on channel c's node, there whatever the
    # render graph holds (`build` adds the eight); plan 35 V2: `channel.<c>`
    seg = pid.split(".")
    return rgraph.channel_name(seg[1]) if len(seg) >= 3 else None


def _view_owner(pid: str, ctx: _Ctx) -> str | None:
    # plan 33 U: the face pattern and its media layer (`view.pattern*`,
    # `view.media_*`) are the pattern node's; the rest of `view.*` the shape's
    key = pid.partition(".")[2]
    return "pattern" if key.startswith(("pattern", "media_")) else "shape"


def _switch_owner(pid: str, ctx: _Ctx) -> str | None:
    # plan 33 S: `switch[.<n>].select` on its switch's node
    return pid.rpartition(".")[0] or None


def _resize_owner(pid: str, ctx: _Ctx) -> str | None:
    # plan 34 T5: `resize[.<n>].<key>` on its resize's node
    return pid.rpartition(".")[0] or None


# a param's group → the canvas node that owns it: a node id, or a rule
# over the param id (an instance's number, an effect's name). Plan 35 V2:
# the ids are the wired frame's, the params keep theirs (`graph.
# param_prefix`: `dream.*` the look-back's, `ghost.2.*` hands 2's). A node
# the section does not name (no look-back, no backdrop) leaves the param
# to its group's node. `CAMERA` is the shared camera's node, the rig's,
# which no section names. A group not listed here has no render node: a
# node per group (`group:<group>`)
OWNERS: dict[str, str | Callable[[str, _Ctx], str | None]] = {
    "view": _view_owner,
    "rot": "shape",
    "pattern": "shape",
    # plan 33 U: the backdrop's params on its node, a switch's pick on its switch
    "backdrop": "backdrop",
    "switch": _switch_owner,
    "resize": _resize_owner,
    "ghost": _hands_owner,
    "cloud": _cloud_owner,
    "dream": rgraph.LOOKBACK,
    "fx": _effect_owner,
    "camera": CAMERA,
    "eye": CAMERA,
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
    """The render node (`render:<name>`, or `render:camera`) that owns param
    `p`, or None: no render node does (or not in this graph)."""
    rule = OWNERS.get(p.group)
    if rule is None:
        return None
    name = rule(p.id, ctx) if callable(rule) else rule
    if name == CAMERA:
        return f"render:{CAMERA}"
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


# ---------------------------------------------------------------- the wired frame (plan 35 G)
#
# The preset's graph is a wired frame (plan 35): every node of the picture,
# the shape to the outputs, is a name of the section's entries or wires, in
# the owner's ids (V2, row 373). The canvas draws the section itself: a
# node per name (`frame_names`), a cable per wire, All outputs and each
# window always, the eight channels (idle while empty and unwired, plan 28
# N9's idle line), the rig's camera and clouds. Each node's `ref` is the
# render node the renderer built for that name, else a stand-in of its
# kind (`_stand_in`: never built into a graph, never run), so its area, its
# side panel and its page are its kind's whatever was built. A node the
# section declares or wires that reaches no sink (`unreached`) is drawn
# faint, "reaches nothing", its wires in, so it can be wired on. Nothing
# of the old frame's plumbing (`frame`, `fx`, `grounded`, `capture`, the
# pipelines' composites and ends) is drawn: none of it is a node any more.

REACHES_NOTHING = "reaches nothing"     # the spec's canvas word for an unreached node
MAKER_KINDS = ("effect", "composite", "switch")    # (`unreached` before the wired frame)
D1_AFTER = "sits after"     # a cable drawn from a D1 `after` effect (`build`, `returns`)

# V (the owner, 2026-10-24, row 373): a node's title by its kind …
LABELS: dict[str, str] = {
    "scene": "Scene", "shape": "Shape", "hands": "Hands", "layer": "Hands layer",
    "guide": "Hands guide", "cloud": "Point cloud", "camera": "Camera",
    "backdrop": "Backdrop", "lookback": "Look-back", "pattern": "Faces pattern",
    "channel": "Channel", "composite": "Composite", "switch": "Switch", "delay": "Delay",
    "resize": "Resize", "echo": "Echo", "dream": "Dream", "copy": "copy of",
    "output": "Output", rgraph.ALL_OUTPUTS: "All outputs", rgraph.GROUND: "Ground",
}
# … and its hover, one line (V's hover column; an effect says its file's
# own `@tip` when it has one)
HOVERS: dict[str, str] = {
    "shape": "The polytope. Its faces show the faces pattern, or the picture wired into faces.",
    "scene": "Draws the shape and any hands wired into it, through the camera.",
    "hands": ("The tracked hands as geometry: wire them into a scene, or draw them alone as "
              "a hands layer."),
    "layer": "The hands drawn alone, to lay over a picture or put through effects.",
    "guide": "The hands' labels and tethers, laid over last and never bent.",
    "cloud": "A listed cloud device, drawn in every scene.",
    "camera": "The shared eye every scene draws through.",
    "backdrop": "Lays the scene over a picture, at backdrop alpha.",
    "lookback": ("Echoes and the dream of past frames, over its picture; records what is "
                 "wired into capture."),
    "pattern": ("What the faces show unless a picture is wired into them, and its media "
                "layer."),
    "channel": "A clip, still or live feed.",
    "effect": "An effect: its knobs, on the picture wired into its image.",
    "copy": "The same effect, with its knobs, on another picture.",
    "composite": "Lays one picture over another.",
    "switch": "Picks one of eight.",
    "delay": "Last frame's picture.",
    "resize": "A crop at its own size.",
    "echo": "The k-th newest look-back frame.",
    "dream": "The dream buffer.",
    "output": "A window: shows its picture, the hands over it, the guide over all.",
    rgraph.ALL_OUTPUTS: ("The rig's bus: a window shows it by a cable from here (the show's), "
                         "unless the preset wires that port itself."),
    # R13: `ground`, a source with no render node, drawn so its wires can be seen and deleted
    rgraph.GROUND: ("A window's background where nothing is drawn — the clear colour, or "
                    "see-through in overlay: wired into an output's port, that port shows it."),
}
# the words a delete or an add says (plan 35 G)
OUTPUT_UNWIRED = "{label} is a window of this rig: its wires are gone, it shows its ground"
ALL_UNWIRED = ("All outputs stays (every window reads it): its wires are gone, so the "
               "windows show their own wires, else their ground")
# plan 36 T1 (W1, D1): the rig's bus cables from All outputs into each
# window (`graph.RigWires`, held by the open show), in words
BUS_SAID = ("the rig's cable (the show's, not the preset's): All outputs' {port} on "
            "{label} — cut it and {label} shows nothing there")
BUS_IDLE = "nothing is wired into All outputs' {port}"
BUS_SAME_PORT = "All outputs' {port} goes into a window's {port} (output.1.{port} …)"
BUS_NO_SHOW = "no show is open: the cables from All outputs are the show's"
BUS_NO_EFFECT = ("{wire} is the rig's cable: put the effect on All outputs' picture, or "
                 "wire the window a picture of its own")
# plan 36 T2 (W2): a listed cloud's wire into the scene, the rig's too
CLOUD_SAID = ("the rig's cable (the show's, not the preset's): this cloud drawn in the "
              "scene — cut it and the scene draws no cloud")
CLOUD_IDLE = "nothing reaches the scene: the cloud is not drawn"
CLOUD_INTO_SCENE = "{cloud} is a cloud device: its one wire is into scene.geometry"
# plan 36 T5 (W5): the picker's starters ▸ — each a pre-wired group, one
# undo step, every node and cable ordinary after it. (key, the item's words)
STARTERS = (("scene", "scene chain"), ("tracers", "tracers"),
            ("tracers+dream", "tracers + dream"), ("dream", "dream on a picture"),
            ("backdrop", "channel to backdrop"))
# the starters a picture cable's menu offers, that cable their picture
CABLE_STARTERS = ("tracers", "tracers+dream", "dream")
# the scene chain: a new preset's whole section and the first starter —
# shape → scene → All outputs, plain faces (no pattern wire)
SCENE_CHAIN = (("shape", "scene.geometry"), ("scene", f"{rgraph.ALL_OUTPUTS}.image"))
NEW_CHAIN = ("shape", "scene", rgraph.ALL_OUTPUTS)   # its nodes, left to right
STARTER_SAID = "scene chain: shape → scene → All outputs"
NO_STARTER = "no starter {which!r}: the starters are " + ", ".join(w for _, w in STARTERS)
NO_CABLE_STARTER = "{label} starts from no cable: pick it from the canvas's starters"
IN_ALREADY = "{label} is in the graph already"
NOTHING_TO_DELETE = "nothing to delete: {what} has no wires"
NO_SUCH_WIRE = "{wire}: no such wire"
NO_SUCH_COPY = "copy of {of}: no such effect instance in the graph"


def kind_of(name: str) -> str | None:
    """A canvas name's kind (plan 35 G): a wired frame's (`graph.
    wire_node_kind(…, wired=True)`), All outputs' own key, the rig's camera
    and clouds, and (R13) `ground` — no render node, but drawn so its wires
    are seen; None for a name no wired frame has a node for (an old id,
    `frame`, `fx`)."""
    if not isinstance(name, str):
        return None
    if name == rgraph.ALL_OUTPUTS:
        return rgraph.ALL_OUTPUTS
    if name == CAMERA:
        return CAMERA
    if name == rgraph.CLOUD_KIND or name.startswith(f"{rgraph.CLOUD_KIND}."):
        return "cloud"
    kind = rgraph.wire_node_kind(name, wired=True)
    return None if kind in ("frame", "fx") else kind


def _takes(kind: str | None) -> dict[str, str]:
    """A canvas kind's input ports (`graph.WIRED_TAKES`; All outputs' are an output's)."""
    if kind == rgraph.ALL_OUTPUTS:
        kind = "output"
    return rgraph.WIRED_TAKES.get(kind or "", {})


def _makes(kind: str | None) -> str | None:
    """What a canvas kind puts out (`graph.WIRED_MAKES`; a cloud geometry)."""
    if kind == "cloud":
        return GEOMETRY
    return rgraph.WIRED_MAKES.get(kind or "")


def _slot_name(slots, n: int) -> str:
    if isinstance(slots, Mapping):
        return str(slots.get(n) or "")
    for sl in slots or ():
        if getattr(sl, "n", None) == n:
            return str(getattr(sl, "name", "") or "")
    return ""


def label_of(name: str, slots=(), *, of: str = "") -> str:
    """Node `name`'s title on the canvas (V, `LABELS`): `hands.2` "Hands 2",
    `channel.a` "Channel A", `hands.2.layer` "Hands layer 2", `echo.3` "Echo
    3", `copy.2` of `acid` "copy of acid (2)", an effect its instance name
    with the dot a space ("acid 2"), a window its config name (`slots`: the
    outputs, each with `n` and `name`, or {n: name}), else "Output N"."""
    kind = kind_of(name)
    if kind == rgraph.ALL_OUTPUTS:
        return LABELS[kind]
    if kind == "output":
        n = int(name.partition(".")[2])
        return _slot_name(slots, n) or f"{LABELS['output']} {n}"
    if kind == "effect":
        return name.replace(".", " ")
    if kind == "copy":
        n = rgraph.split_instance(name)[1]
        what = f"{LABELS['copy']} {of}" if of else "copy"
        return what if n == 1 else f"{what} ({n})"
    if kind == "channel":
        return f"{LABELS['channel']} {name.partition('.')[2].upper()}"
    if kind in ("layer", "guide"):
        n = rgraph.split_instance(rgraph.hands_of(name))[1]
        return LABELS[kind] if n == 1 else f"{LABELS[kind]} {n}"
    if kind in LABELS:
        rest = name.partition(".")[2]
        return f"{LABELS[kind]} {rest}" if rest else LABELS[kind]
    return name


def params_of(name: str, of: str = "") -> str:
    """The prefix node `name`'s params are found by (V2: `graph.
    param_prefix` — params keep their ids); a copy's knobs are its
    original's (`fx.<of>`)."""
    kind = kind_of(name)
    if kind == "copy" and of:
        return f"fx.{of}"
    if kind in (rgraph.ALL_OUTPUTS, "cloud", None):
        return name
    return rgraph.param_prefix(name)


def hover_of(name: str, slots=(), *, of: str = "", tip: str = "") -> str:
    """Node `name`'s hover (V, `HOVERS`): what it is in one line (an
    effect's own `@tip`, when its file has one), then its id and, where it
    differs, its params' prefix — "… · id lookback · params dream.*", so
    `dream.fade` under a node called Look-back reads why."""
    kind = kind_of(name)
    text = tip if kind == "effect" and tip else HOVERS.get(kind or "", "")
    out = f"{text} · id {name}" if text else f"id {name}"
    pre = params_of(name, of)
    return out if pre == name else f"{out} · params {pre}.*"


def side_head(n: VNode) -> str:
    """A frame node's side-panel header (V2): its title, its id and, where it
    differs, its params' prefix — "Look-back · lookback · params dream.*"."""
    name = n.id.partition(":")[2]
    of = getattr(n.ref, "effect", "") if kind_of(name) == "copy" else ""
    pre = params_of(name, of)
    head = f"{n.label} · {name}"
    return head if pre == name else f"{head} · params {pre}.*"


def _tip(reg, name: str) -> str:
    """Effect instance `name`'s file's `@tip`, its first sentence (a hover is
    one line); "" with no FxState to ask."""
    specs = getattr(getattr(reg, "fx_state", None), "specs", None) or {}
    spec = specs.get(name) or specs.get(rgraph.split_instance(name)[0])
    tip = str(getattr(spec, "tip", "") or "")
    head, dot, _ = tip.partition(". ")
    return (head + "." if dot else tip).strip()


ECHO_PINS = 4      # plan 36 T4: the echo pins a look-back always draws (echo.1 … echo.4)


def echo_pins(name: str, spec) -> list[str]:
    """Look-back `name`'s echo pins drawn on the canvas (plan 36 T4): the
    newest few (`ECHO_PINS`) and every other one a wire of `spec` reads."""
    wired = {k for w in (spec.all_wires() if spec is not None else ())
             for got in [rgraph.echo_of(w.src)] if got is not None and got[0] == name
             for k in [got[1]]}
    return [f"{name}.echo.{k}" for k in sorted({*range(1, ECHO_PINS + 1), *wired})]


def frame_names(spec) -> list[str]:
    """Every node wired frame `spec` names, once, in section order: its
    entries' (the hands, the effects, then the rest as read), then each
    wire's ends (`ground` too, R13: drawn so its wires are seen) — with the hands node each
    layer or guide is of just before it (the hands' params are on that
    node). Plan 36 T2: a pin (`scene.cover`) is its node's."""
    if spec is None:
        return []
    raw: list[str] = [rgraph.wired_hands_name(h.n) for h in spec.hands]
    raw += [e.name for e in spec.effects]
    for _, got in spec.others:
        name = getattr(got, "name", None)
        if isinstance(name, str):
            raw.append(name)
    for w in spec.all_wires():
        raw += [w.src, w.node]
    out: list[str] = []
    for name in dict.fromkeys(rgraph.pin_node(x) or x for x in raw):
        kind = kind_of(name)
        if kind is None:
            continue
        if kind in ("layer", "guide") and rgraph.hands_of(name) not in out:
            out.append(rgraph.hands_of(name))
        if name not in out:
            out.append(name)
    return out


def unreached(spec) -> frozenset[str]:
    """The nodes of section `spec` that reach no sink (`graph.reaches`):
    drawn faint, never run. Plan 35 G: in a wired frame every kind — a
    node declared or wired with no path to an output's port, All outputs'
    or the look-back's capture (plan 36 T2: a hands node by its wire into a
    layer's or a guide's `hands`, no longer by name; the windows and All
    outputs are the sinks, never faint). Before the wired frame (a section
    a test reads as it stands): the effects, composites and switches, as
    plan 33 drew them. A D1-placed effect sits where it is placed, so it
    reaches."""
    if spec is None:
        return frozenset()
    got = set(rgraph.reaches(spec)) | {e.name for e in spec.effects if e.placed}
    if getattr(spec, "wired", False):
        # (R15: an effect or a copy no wire feeds reads nothing — never built,
        # faint, its outs kept)
        fed = {w.node for w in spec.all_wires() if w.port == "image"}
        got -= {n for n in got if kind_of(n) in ("effect", "copy") and n not in fed
                and n not in {e.name for e in spec.effects if e.placed}}
        return frozenset(n for n in frame_names(spec) if n not in got
                         and kind_of(n) not in ("output", rgraph.ALL_OUTPUTS, rgraph.GROUND))
    names = {e.name for e in spec.effects} | {s.name for s in spec.switches}
    names |= {c.name for c in spec.composites()}
    names |= {n for w in spec.wires for n in (w.src, w.node)
              if rgraph.wire_node_kind(n) in MAKER_KINDS}
    return frozenset(n for n in names if n not in got)


class GroundNode(rgraph.Node):
    """`ground` on the canvas (R13): the source a wire into an output's port
    names to show the window's background there. No render node is ever
    built for it (the output clears to its ground); this stands in so the
    wire is drawn, and can be deleted, like any other."""

    KIND = "ground"
    OUTPUT = IMAGE


# a frame kind → the render class its node is (a built one is taken only
# when it is of this class: a guide split out of its layer is the layer's
# node, the backdrop the composite that lays the scene on; each such stands in)
FRAME_CLASS: dict[str, type] = {
    "scene": rgraph.Scene, "shape": rgraph.Shape, "hands": rgraph.Hands,
    "layer": rgraph.HandsLayer, "guide": rgraph.Readout, "cloud": rgraph.PointCloud,
    "backdrop": rgraph.BackdropNode, "lookback": rgraph.History,
    "pattern": rgraph.PatternNode, "channel": rgraph.MediaNode, "effect": rgraph.Effect,
    "copy": rgraph.Copy, "composite": rgraph.Composite, "switch": rgraph.SwitchNode,
    "delay": rgraph.Delay, "resize": rgraph.ResizeNode, "echo": rgraph.EchoNode,
    "dream": rgraph.DreamNode, "output": rgraph.Output, rgraph.ALL_OUTPUTS: rgraph.Output,
    rgraph.GROUND: GroundNode,
}


def _stand_in(name: str, spec=None) -> rgraph.Node | None:
    """A render node of kind `name`'s for the canvas to draw where the
    renderer built none (unreached, or not reached this frame): never built
    into a graph, never run. Every kind of a wired frame has one; a copy's
    `of` and a composite's blend are the section's (`spec`)."""
    kind = kind_of(name)
    if kind is None:
        return None
    rest = name.partition(".")[2]
    if kind == "effect":
        return rgraph.Effect(name, node=name)
    if kind == "copy":
        of = next((c.of for c in (getattr(spec, "copies", ()) or ()) if c.name == name), "")
        return rgraph.Copy(name, of)
    if kind == "composite":
        c = next((c for c in (spec.composites() if spec is not None else ()) if c.name == name),
                 None)
        return rgraph.Composite(name, blend=c.blend if c is not None else "over")
    if kind == "channel":
        return rgraph.MediaNode(name, rest)
    if kind == "cloud":
        return rgraph.PointCloud(name, "")
    if kind == "echo":
        got = rgraph.echo_of(name)                   # (plan 36 T4: a look-back's pin)
        return rgraph.EchoNode(name, got[1], lookback=got[0]) if got is not None else None
    if kind in ("output", rgraph.ALL_OUTPUTS):
        return rgraph.Output(name, int(rest) - 1 if rest.isdecimal() else -1)
    if kind == CAMERA:
        return None
    return FRAME_CLASS[kind](name)


def _built(rnodes: Iterable[rgraph.Node]) -> dict[str, rgraph.Node]:
    """The render nodes the renderer built, by the canvas name each stands
    for: an effect by its instance, a channel by `channel.<c>` (its first
    node: the backdrop's own and a wire's are one channel), the rest by
    name — each only when it is of its kind's class (`FRAME_CLASS`)."""
    out: dict[str, rgraph.Node] = {}
    for r in rnodes:
        if isinstance(r, rgraph.Copy):
            name = r.name
        elif isinstance(r, rgraph.Effect):
            name = r.effect
        elif isinstance(r, rgraph.MediaNode):
            name = rgraph.channel_name(r.channel)
        else:
            name = r.name
        cls = FRAME_CLASS.get(kind_of(name) or "")
        if cls is None or not isinstance(r, cls) or name in out:
            continue
        if cls is rgraph.Effect and isinstance(r, rgraph.Copy):
            continue
        out[name] = r
    return out


def frame_of(spec, render_graph=None):
    """The wired frame the canvas draws (plan 35 G): the preset's section
    when it is one (every load's); with none, the frame the renderer drew
    (its wiring), else `{"frame": "wired"}`'s nothing. Plan 36 T3 (W3):
    nothing else — a section or a wiring from before the wired frame is
    an old preset's words, which only the one-way migration reads, so the
    canvas draws the empty frame for it."""
    if spec is not None and getattr(spec, "wired", False):
        return spec
    wiring = getattr(render_graph, "wiring", None) if spec is None else None
    if wiring is not None and getattr(wiring, "wired", False):
        return rgraph.GraphSpec(
            hands=tuple(wiring.nodes()), laid=wiring.blend, laid_on=wiring.laid_on,
            others=(*(("composite", c) for c in wiring.composites),
                                       *(("copy", c) for c in wiring.copies)),
            wires=tuple(wiring.wires), wired=True)
    return rgraph.read_graph({rgraph.FRAME_KEY: rgraph.WIRED_FRAME})


# (plan 34 T4: a resize of the media alone too — `channel.a → resize →
# acid.2` runs on from the media, as a switch over the channels does)
MEDIA_MADE = (rgraph.Effect, rgraph.Composite, rgraph.SwitchNode, rgraph.ResizeNode)


def media_made(r) -> bool:
    """Is render node `r` an effect, composite or switch whose picture is
    made of the media alone (plan 33 T6's layout rule): every path back
    from it through its picture inputs starts at a channel or the pattern,
    and there is one. Such a node is a branch of the media and sits in the
    media area, so `channel.a → acid.2 → shape.faces` runs left to right."""
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
        if isinstance(n, rgraph.Scene):
            # a scene picture (plan 36 T2: its faces' pattern is a wire now,
            # and a scene of patterned faces is still the scene)
            return False
        ins = [x for x in getattr(n, "inputs", {}).values() if x is not None]
        if not ins:
            if n is not r:
                return False            # a scene picture (the look-back, the scene …)
            continue
        todo.extend(ins)
    return heads > 0


def build(table: Bindings, reg: Registry, router: Router | None = None, devices=None,
          render_graph: rgraph.Graph | None = None, spec=None, *, lanes=None,
          bands: Iterable[str] | None = None, template=None, slots=(), rig=None) -> View:
    """The view of `table`, `reg`, `router`, the device registry `devices`
    and the render graph `render_graph` (the renderer's last), with the
    preset's graph `spec` kept on the view. `lanes` are the analyzer's
    lanes this frame, normalised (None: not live); `bands` their names
    (else the Router's published ``lane`` labels); `template` the loaded
    preset's desk template as ``(name, rows)`` (plan 28 N5), None when it
    names none; `slots` the rig's outputs (each with `n` and `name`: a
    window's title is its config name, plan 35 G); `rig` the rig's own
    wires (plan 36 T1, `graph.RigWires`: the bus cables drawn), else the
    render graph's — what it was built with."""
    view = View(spec=spec)
    if rig is None:
        rig = getattr(render_graph, "rig", None)
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

    # ---- the wired frame's nodes (plan 35 G): the section's, in the owner's ids ----
    ctx = _Ctx()
    rnodes = list(render_graph.order) if render_graph is not None else []
    frame = frame_of(spec, render_graph)
    built = _built(rnodes)
    copies = {c.name: c.of for c in frame.copies}
    # the canvas's names: the eight channels always (plan 32 T10: what a
    # wire starts from), the rig's clouds, the section's names, All outputs
    # and every window the renderer drew (and any a wire names)
    names: list[str] = [rgraph.channel_name(c) for c in rgraph.MEDIA_CHANNELS]
    # (plan 36 T2: every listed cloud, built or not — one whose wire the
    # show has cut is drawn too, to join again)
    roles = tuple(getattr(render_graph, "clouds", ()) or ())
    names += [rgraph.cloud_name(i) for i in range(len(roles))]
    names += [r.name for r in rnodes if isinstance(r, rgraph.PointCloud)]
    names += frame_names(frame)
    outs = {r.name for r in rnodes if isinstance(r, rgraph.Output)}
    outs |= {n for n in names if kind_of(n) == "output"}
    names = [n for n in dict.fromkeys(names) if kind_of(n) not in ("output", rgraph.ALL_OUTPUTS)]
    names += [rgraph.ALL_OUTPUTS, *sorted(outs, key=lambda n: int(n.partition(".")[2]))]
    gone = unreached(frame)
    refs: dict[str, rgraph.Node] = {}
    stood: set[str] = set()
    for name in names:
        r = built.get(name)
        if r is None:
            r = _stand_in(name, frame)
            if r is None:
                continue
            stood.add(name)
        refs[name] = r
    # a stand-in's inputs are the section's wires into it (what the layout
    # reads its picture as made of: `media_made`)
    for w in frame.all_wires():
        r, src = refs.get(w.node), refs.get(w.src)
        if w.node in stood and src is not None and w.port in r.INPUTS:
            r.inputs[w.port] = src
    for name, r in refs.items():
        kind = kind_of(name)
        vkind = ("channel" if kind == "channel" else
                 "output" if kind in ("output", rgraph.ALL_OUTPUTS) else "render")
        of = copies.get(name, "")
        n = add_node(VNode(f"render:{name}", vkind, label_of(name, slots, of=of), ref=r,
                           status=hover_of(name, slots, of=of,
                                           tip=_tip(reg, name) if kind == "effect" else "")))
        for port, typ in _takes(kind).items():
            add_port(n, VPort(f"rin:{name}/{port}", port, IN, typ))
        made = _makes(kind)
        if made is not None:
            add_port(n, VPort(f"rout:{name}", made, OUT, made))
        if kind == rgraph.ALL_OUTPUTS:           # plan 36 T1: the bus's pins, one a port
            for port in rgraph.BUS_PORTS:
                add_port(n, VPort(f"rout:{name}.{port}", port, OUT, IMAGE))
        for pin, owner in rgraph.PINS.items():   # plan 36 T2: the scene's cover and depth
            if owner == name:
                typ = rgraph.WIRED_MAKES[kind_of(pin)]
                add_port(n, VPort(f"rout:{pin}", pin.rpartition(".")[2], OUT, typ))
        if kind == "lookback":                   # plan 36 T4: its own frames, pins
            for pin in echo_pins(name, frame):
                add_port(n, VPort(f"rout:{pin}", pin[len(name) + 1:], OUT, IMAGE))
        if isinstance(r, rgraph.PointCloud) and ctx.first_cloud is None:
            ctx.first_cloud = name
    ctx.names = set(refs)
    ctx.effect_node = {name: name for name in refs if kind_of(name) == "effect"}
    ctx.effects = sorted(ctx.effect_node, key=len, reverse=True)   # `acid.2` before `acid`

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
            if rid == f"render:{CAMERA}" and rid not in nodes:
                add_node(VNode(rid, "render", label_of(CAMERA), status=hover_of(CAMERA)))
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
    # plan 35 G: each wire of the section, as it stands, a render cable —
    # `ground`'s from the Ground node (R13), a wire into a
    # window this rig has not open dormant (plan 35 T4: it builds nothing)
    windows = {r.name for r in rnodes if isinstance(r, rgraph.Output)}
    # (plan 30 D1's `after X`, kept in an old preset's frame: what reads X
    # reads the effect — drawn from it, the cable still X's wire)
    after = {e.where[1]: e.name for e in frame.effects
             if e.where is not None and e.where[0] == "after"
             and not e.where[1].startswith("output.")}
    for w in frame.all_wires():
        lay = after.get(w.src) if w.node != after.get(w.src) else None
        src, dst = f"rout:{lay or w.src}", f"rin:{w.node}/{w.port}"
        if src not in view.pins or dst not in view.pins:
            continue
        shut = (render_graph is not None and kind_of(w.node) == "output"
                and w.node not in windows)
        said = (f"no {w.node} this frame" if shut else
                f"{lay} {D1_AFTER} {w.src}: what reads {w.src} reads it" if lay else "")
        view.cables.append(VCable(cable_id(f"wire:{w.src}>{w.node}/{w.port}"), src, dst,
                                  _takes(kind_of(w.node)).get(w.port, IMAGE), ref=w,
                                  kind="render", dormant=shut, off=shut, label=said))
    # plan 36 T1 (W1, D1): the rig's bus cables, `output.all.<port> →
    # output.<n>.<port>` — each standing one the show has not cut, into
    # every window on the canvas, but where the preset wires that port
    # itself (its own wire takes it: one wire into a port, always drawn);
    # dormant into a window not open, or while nothing feeds that port of
    # All outputs. A render cable like any: delete cuts it (the show's)
    owned = {w.dst for w in frame.all_wires()}
    feeds = {w.port for w in frame.all_wires() if w.node == rgraph.ALL_OUTPUTS}
    standing = rgraph.RigWires() if rig is None else rig
    for name in sorted((x for x in refs if kind_of(x) == "output"),
                       key=lambda x: int(x.partition(".")[2])):
        n = int(name.partition(".")[2])
        for w in standing.present(rgraph.bus_wire(n, p) for p in rgraph.BUS_PORTS):
            src, dst = f"rout:{w.src}", f"rin:{w.node}/{w.port}"
            if w.dst in owned or src not in view.pins or dst not in view.pins:
                continue
            shut = render_graph is not None and name not in windows
            idle = w.port not in feeds
            said = (f"no {name} this frame" if shut else BUS_IDLE.format(port=w.port) if idle
                    else BUS_SAID.format(port=w.port, label=label_of(name, slots)))
            view.cables.append(VCable(cable_id(f"bus:{w.src}>{w.node}/{w.port}"), src, dst,
                                      IMAGE, ref=w, kind="render", dormant=shut or idle,
                                      off=shut, label=said))
    # plan 36 T2 (W2): each listed cloud's wire into the scene — the rig's,
    # standing until the show cuts it, cut and joined like a bus cable;
    # dormant while nothing reaches the scene (the cloud is not built)
    for i in range(len(roles)):
        w = rgraph.cloud_wire(i)
        src, dst = f"rout:{w.src}", f"rin:{w.node}/{w.port}"
        if not standing.has(w) or src not in view.pins or dst not in view.pins:
            continue
        idle = "scene" in gone
        view.cables.append(VCable(cable_id(f"rig:{w.src}>{w.node}/{w.port}"), src, dst,
                                  GEOMETRY, ref=w, kind="render", dormant=idle,
                                  label=CLOUD_IDLE if idle else CLOUD_SAID))

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
        if c.kind == "render":
            continue
        for nid in (view.pins.get(c.src_port, ("",))[0], view.pins.get(c.dst_port, ("",))[0]):
            ref = nodes[nid].ref if nid in nodes else None
            if isinstance(ref, rgraph.Effect):
                cabled.add(ref.effect)
    for n in nodes.values():
        n.area = area_of(n)
        # plan 33 U, plan 35 G: a node of the section that reaches nothing
        # is drawn faint, and so never idle — it was just added, or it
        # waits to be wired in; (plan 35 G) a channel with nothing in its
        # bin and no cable sits on MEDIA's idle line, as an idle macro does
        n.faint = n.kind in FRAME_VKINDS and n.id.partition(":")[2] in gone
        n.idle = not n.faint and (
            (n.kind == "channel" and is_idle(n, macros, named) and channel_empty(n, reg))
            or (n.kind != "channel" and is_idle(n, macros, named))
            or (n.kind == "render" and effect_off(n, reg) and n.ref.effect not in cabled))
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
        pick = isinstance(n.ref, rgraph.SwitchNode)     # its summary says its pick
        for port in n.ports:
            if shut and not port.patched and port.direction != OUT and not (
                    pick and port.param is not None):
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
# backdrop under the scene) and by the faces.
#
# Plan 35 G: the frame's areas by primitive, the way a picture is made —
# media, the scene, the look-back, the effects, the outputs — where the
# geometry and the shaders were: the frame is ordinary nodes now, so the
# areas name what each is, not the pipelines it used to be part of.
CONTROLLERS, AUDIO, MODULATION, MEDIA = "controllers", "audio", "modulation", "media"
SCENE_AREA, LOOKBACK_AREA, EFFECTS_AREA, OUTPUTS_AREA = "scene", "lookback", "effects", "outputs"
OTHER = "other"
AREAS = (CONTROLLERS, AUDIO, MODULATION, MEDIA, SCENE_AREA, LOOKBACK_AREA, EFFECTS_AREA,
         OUTPUTS_AREA)                                       # left to right
SHARES = {OTHER: AUDIO}       # an area drawn under another's, in its column
ORDER = (CONTROLLERS, AUDIO, OTHER, MODULATION, MEDIA, SCENE_AREA, LOOKBACK_AREA, EFFECTS_AREA,
         OUTPUTS_AREA)

# the one table: a node's area by its kind, a group node by its id
# (``group:<param group>``), a render node by its class (or a base class)
AREA: dict[str, str] = {
    # by kind
    "device": CONTROLLERS, "source": CONTROLLERS, "template": CONTROLLERS,
    "analyzer": AUDIO,
    "lfo": MODULATION, "env": MODULATION, SEQ: MODULATION,
    "modifier": MODULATION, "macro": MODULATION,
    "output": OUTPUTS_AREA, "channel": MEDIA,
    # a group node, by its param group
    "group:band": AUDIO, "group:bands": AUDIO, "group:tempo": AUDIO,
    "group:master": AUDIO, "group:audio": AUDIO, "group:scene": AUDIO,
    "group:lfo": MODULATION, "group:mod": MODULATION, "group:macro": MODULATION,
    "group:env": MODULATION, "group:seq": MODULATION,
    "group:view": SCENE_AREA, "group:rot": SCENE_AREA, "group:pattern": SCENE_AREA,
    "group:camera": SCENE_AREA, "group:eye": SCENE_AREA, "group:ghost": SCENE_AREA,
    "group:hands": SCENE_AREA, "group:cloud": SCENE_AREA, "group:backdrop": SCENE_AREA,
    "group:dream": LOOKBACK_AREA,
    "group:fx": EFFECTS_AREA,
    "group:output": OUTPUTS_AREA, "group:overlay": OUTPUTS_AREA,
    "group:media": MEDIA, "group:switch": MEDIA,
    # a render node, by its class. The scene: what it draws and what it is
    # laid on — the shape, the hands, their layers and guides, a cloud, the
    # camera it draws through, the backdrop
    f"render:{CAMERA}": SCENE_AREA,
    "Shape": SCENE_AREA, "Hands": SCENE_AREA, "HandsLayer": SCENE_AREA, "Readout": SCENE_AREA,
    "PointCloud": SCENE_AREA, "Scene": SCENE_AREA, "BackdropNode": SCENE_AREA,
    # the look-back: the ring's pictures
    "History": LOOKBACK_AREA, "EchoNode": LOOKBACK_AREA, "DreamNode": LOOKBACK_AREA,
    # the effects and what lays or crops a picture between them (a copy is
    # an `Effect`: found by its base class)
    "Effect": EFFECTS_AREA, "Composite": EFFECTS_AREA, "ResizeNode": EFFECTS_AREA,
    # the windows and All outputs
    "Output": OUTPUTS_AREA, "GroundNode": OUTPUTS_AREA,
    # the media channels (plan 32 T10), and (plan 33 U) the pictures made
    # beside them: the pattern the faces draw, a switch picking one of them,
    # a delay's last frame — and any effect or composite made of the media
    # alone (`media_made`, by `area_of`)
    "MediaNode": MEDIA, "PatternNode": MEDIA, "SwitchNode": MEDIA, "Delay": MEDIA,
}
TITLES = {CONTROLLERS: "CONTROLLERS", AUDIO: "AUDIO", OTHER: "OTHER",
          MODULATION: "MODULATION", MEDIA: "MEDIA", SCENE_AREA: "SCENE",
          LOOKBACK_AREA: "LOOK-BACK", EFFECTS_AREA: "EFFECTS", OUTPUTS_AREA: "OUTPUTS"}
# a title too long for its room at the floor size (review round 1)
SHORT_TITLES = {CONTROLLERS: "CTRL", AUDIO: "AUD", OTHER: "OTH", MODULATION: "MOD",
                MEDIA: "MED", SCENE_AREA: "SCN", LOOKBACK_AREA: "LKB", EFFECTS_AREA: "FX",
                OUTPUTS_AREA: "OUT"}
# 2026-10-26 (the laptop's own screen): the canvas's text, boxes, pins and
# spacing all a quarter bigger than the panel's — one factor, so the
# layout's units still hold what the page draws in them; each unit whole
# (the editor puts a node on a whole pixel: a half one reads as a drag)
SCALE = 1.25
COL_W = float(round(260 * SCALE))  # canvas units between two columns
ROW_H = float(round(22 * SCALE))   # one port line
HEAD_H = float(round(34 * SCALE))  # a node's title and padding
GAP = float(round(28 * SCALE))     # between two nodes of a column
TITLE_H = float(round(64 * SCALE))  # an area's title, above its first node
IDLE_H = HEAD_H        # an area's idle line


def chain_layout(names: Iterable[str], at: tuple[float, float]) -> dict[str, list[int]]:
    """Render nodes `names` laid left to right from `at` (layout units),
    one column (`COL_W`) apart on one row: their layout map entries by
    canvas id (plan 36 T5: a new preset's chain, a starter's group)."""
    x, y = at
    return {f"render:{n}": [round(x + i * COL_W), round(y)] for i, n in enumerate(names)}


def area_of(n: VNode) -> str:
    """The area node `n` is laid out in (`AREA`): a group node by its id, a
    render node by its class or a base of it (a render class no row names
    is an effect's: it is in the picture's chain), every other node by its
    kind; a node the table does not name is `OTHER`. Plan 33 T6: an
    effect, composite or switch made of the media alone (`media_made`) is
    the media's."""
    if n.kind == "group" or n.id == f"render:{CAMERA}":
        return AREA.get(n.id, OTHER)
    if n.kind in FRAME_VKINDS and n.ref is not None:
        if media_made(n.ref):
            return MEDIA
        for cls in type(n.ref).__mro__:
            if cls.__name__ in AREA:
                return AREA[cls.__name__]
        return EFFECTS_AREA
    return AREA.get(n.kind, OTHER)


# which kinds may sit idle (`is_idle`): a node of any other kind is always
# drawn — the analyzer, a modifier just picked (it is dropped onto a cable
# next), a render node, a connected device, a placeholder (it has rows);
# plan 35 G: a channel, while its bin is empty too (`channel_empty`)
IDLE_KINDS = ("macro", "lfo", "env", SEQ, "group", "device", "channel")
IDLE_NOUNS = {"macro": ("idle macro", "idle macros"), "lfo": ("idle LFO", "idle LFOs"),
              "env": ("idle envelope", "idle envelopes"),
              SEQ: ("idle sequencer", "idle sequencers"),
              "group": ("idle param group", "idle param groups"),
              "effect": ("off effect", "off effects"),
              "channel": ("empty channel", "empty channels"),
              "off": ("off device", "off devices"), "lost": ("lost device", "lost devices")}
# plan 32 T10 drew the backdrop's group node always; plan 35 G: the
# backdrop is a node of the section, drawn when wired or declared, and its
# group node idles like any group (none is always drawn)
ALWAYS_DRAWN: tuple[str, ...] = ()
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


SHADER_ROW = 4         # the effects' chain wraps into rows of this many columns (Z rows)
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
    wires); the effects' depths wrapped into rows of `SHADER_ROW` (Z order:
    every row left to right; plan 35 G: the outputs are an area of their
    own). The areas follow one another in `AREAS`; `OTHER` takes the
    audio's first column."""
    def gridded(n: VNode) -> bool:
        return not n.idle or (n.area in opened and n.kind in ("render", "channel"))

    nodes = [n for n in view.nodes if n.area and gridded(n)]
    ids = {n.id for n in nodes}
    links = [(a, b) for a, b in _links(view, (*view.cables, *extra))
             if a in ids and b in ids]
    depth = _depths(nodes, links)
    local: dict[str, tuple[int, int]] = {}
    for n in nodes:
        d = depth[n.id]
        if n.area == EFFECTS_AREA:
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
    and row (`rows`: only the effects wrap); the through wires over the
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
    """The ids of the wires that run back by design: inside the effects,
    from one row of the wrapped chain to a later one (the row's last
    output to the next row's first input); (plan 33 T6) a picture the
    scene made, taken back into a sink that sits left of where it was made
    (`TAKEN_BACK`: `lookback → acid.2 → switch.in1`; into the faces, the
    pattern or the backdrop such a picture is a loop — the scene draws
    them — and is never built) — a picture made of the media alone sits
    with the media (`media_made`), so its wire runs right; and (plan 35 G)
    every wire into `lookback.capture` and into a delay's `image`: what is
    kept for the frames after, read back where its ring or its delay sits.
    Every other wire runs right."""
    out = set()
    order = {a: k for k, a in enumerate(AREAS)}
    for c in (*view.cables, *lay.throughs):
        a, b = view.node(node_of(view, c.src_port)), view.node(node_of(view, c.dst_port))
        if a is None or b is None:
            continue
        # (plan 36 T4: what a look-back records is its `image`)
        kept = (isinstance(b.ref, (rgraph.Delay, rgraph.History))
                and c.dst_port.endswith("/image"))
        # (an old preset's D1 `after X` effect, drawn where X's readers read
        # it: it sits with the effects, its reader may sit left of them)
        kept = kept or (c.kind == "render" and f" {D1_AFTER} " in c.label)
        wrapped = (a.area == b.area == EFFECTS_AREA
                   and lay.rows.get(b.id, 0) > lay.rows.get(a.id, 0))
        taken = (order.get(a.area, 0) > order.get(b.area, 0) and isinstance(b.ref, TAKEN_BACK)
                 and c.type == IMAGE)
        if kept or wrapped or taken:
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
    if n.kind in ("modifier", "macro", "render", "channel", TEMPLATE, *BANK_SCHEMES, SEQ):
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
        said = getattr(n.ref, "said", "")   # plan 34 T5: the node's own words
        if said:
            lines.insert(0, said)
        if isinstance(n.ref, rgraph.SwitchNode):
            lines.insert(0, switch_pick(n))
        if n.faint:                         # plan 33 U: unreached, said first
            lines.insert(0, REACHES_NOTHING)
    return lines[:SUMMARY_LINES]


def switch_pick(n: VNode) -> str:
    """A switch node's pick in words, from its `select` port's reading
    (the owner, 2026-10-24: the canvas says which input passes): "picks
    in3", "off" — "off" too while it reads nothing."""
    port = next((p for p in n.ports if p.param is not None), None)
    live = port.live if port is not None else None
    k = 0 if live is None else round(live * len(rgraph.SWITCH_PORTS))
    return f"picks in{k}" if 1 <= k <= len(rgraph.SWITCH_PORTS) else "off"


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
        # plan 36 T5: the nodes the last starter added, left to right (each
        # placed by the page from where the menu opened)
        self.placed: tuple[str, ...] = ()
        self.slots = ()         # plan 35 G: the rig's outputs (a window's name in the words)
        # plan 36 T1: the open show, which holds the rig's own wires (its
        # `rig`, `graph.RigWires`): a bus cable cut or joined lands there
        self.show = None

    # ---- the render graph (plan 28 N4): each returns None (done; its
    # words in `said`) or a refusal in words, nothing changed ----

    def wire(self, src_port: str, dst_port: str, dry: bool = False) -> str | None:
        """A picture (or, into `scene.geometry`, geometry) from `src_port`
        into `dst_port`: a wire of the section. `dry`: only say whether it
        may be."""
        return render_wire(self, src_port, dst_port, dry)

    def wire_refusal(self, src_port: str, dst_port: str) -> str | None:
        """Why `wire` would refuse, changing nothing (the drag's words)."""
        return self.wire(src_port, dst_port, dry=True)

    def unwire(self, cable, dst: str | None = None) -> str | None:
        """Take a render cable (a `VCable`, or its two ends; one port's
        name alone: whatever is wired into it) out of the graph — any wire
        of the section (plan 35 G)."""
        return render_unwire(self, cable, dst)

    def add_node(self, kind: str, file: str | None = None, **settings) -> str | None:
        """The picker (plan 35 G, `picker`): a frame node (once each), a
        hands node, an effect (R25: the file itself when nothing in the
        section holds it, else the lowest free instance, switched on), a
        copy of an instance (`file`), a composite, a switch, plan 34's
        delay, resize, echo (`file`: its index) and dream — each on no wire
        (unreached, faint, until one is wired). The new node's name is
        `added`."""
        return render_add(self, kind, file, **settings)

    def starter(self, which: str = "scene", cable=None) -> str | None:
        """A starter (plan 36 T5, `STARTERS`): its pre-wired group in one
        landing — `cable` (a picture cable: a `VCable` or its two ends) the
        picture a tracers or dream starter is laid on. The nodes it added,
        left to right, are `placed`."""
        return render_starter(self, which, cable)

    def insert_effect(self, cable, file: str) -> Refusal | None:
        """Plan 33 U: effect `file` onto picture cable `cable` (a `VCable`,
        or its two ends: pins or the section's names): `src → new.image`,
        `new → dst`, in one landing (one undo step) — R25: the file itself
        when nothing in the section holds it, else the lowest free instance,
        switched on in the same step."""
        why = render_insert(self, cable, file)
        return Refusal(why) if why is not None else None

    def switch_channels(self, port: str) -> str | None:
        """R28: the picker's "switch over the channels ▸ faces media /
        backdrop" — a new switch over `channel.a … h` into `port`
        (`pattern.media`, `backdrop.image`) at the channel that fed it, one
        undo step (`render_channel_switch`). The switch's name is `added`."""
        return render_channel_switch(self, port)

    def place_effect(self, cable, name: str) -> Refusal | None:
        """Plan 33 U: effect instance `name` (an existing one: a free node
        dropped on a cable, or one dragged out of its place — reordering the
        run is this) taken out of wherever its picture goes, the wires
        either side of it closed over it, and put onto `cable` — one
        landing."""
        why = render_place(self, cable, name)
        return Refusal(why) if why is not None else None

    def drop_node(self, node: str) -> str | None:
        """Delete a render node — any node of the section (plan 35 G): its
        entry and every wire on it go, in one undo step; a window's wires
        go (it is the rig's); the camera and a cloud are the rig's."""
        return render_drop(self, node)

    remove_render_node = drop_node          # N3's name for it (`remove_node`)

    def set_node(self, node: str, **settings) -> str | None:
        """A node's setting: a hands node's `draw`, a composite's `blend`."""
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
        else the `position` fader at 1; from an envelope into a continuous
        param, a push about the base at its headroom (the owner,
        2026-10-24). Route from ▸ (`ui_graph.route_from`) lands the same."""
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
        if kind in FRAME_VKINDS:
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
# picture ports, or geometry into `scene.geometry`, is a wire in the
# preset's `graph` section (`graph.Wire`); the picker adds a node; deleting
# a render node or cable takes it out of the section. Each edit is a new
# section read back through `graph.read_graph` with the build's effect
# files — so a refusal is the very note a preset file would get, in its
# words (the types, the loops: `wire_loops`, over the drawn wires),
# and nothing changes — then landed through the preset's `GraphSection`
# (`land`: the instances' params declared or dropped, the renderer handed
# the new wiring, which builds the graph again), one undo step before it
# (`push`), the preset dirty. The seam with plan 28 N3's modulation edits
# is the port type: image / geometry / mask cables are these
# (`RENDER_TYPES`), value / trigger cables N3's.
#
# Plan 35 G: the section is a wired frame in the owner's ids, and the page
# edits it as it stands — every node and wire of it deletes (the old
# frame's own nodes, its run and its default edges were refused; there
# are none now). What stays refused: a type error, a loop, and the rig's
# own — a window (delete takes its wires: `OUTPUT_UNWIRED`), the camera and
# a cloud (`NOT_REMOVABLE`).


def spec_name(pin: str, render_graph=None) -> tuple[str | None, str | None]:
    """A canvas pin or node id (`rout:<node>`, `rin:<node>/<port>`,
    `render:<node>`), or a name as the preset's graph says it → (that
    name — `hands.2`, `acid.2`, `output.2.hands`, `scene.geometry` —,
    None), or (None, why it is no name a wire may use). Plan 35 G: the
    canvas's names are the section's (V2), so a pin is its name; the
    camera and a cloud are the rig's, no name a section says.
    (`render_graph` is no longer asked: kept for the callers' signature.)"""
    head, _, rest = pin.partition(":")
    if head not in ("rout", "rin", "render") or not rest:
        node = pin if kind_of(pin) is not None else pin.rpartition(".")[0]
        return (pin, None) if kind_of(node) is not None else (None, f"no node {pin!r}")
    name, _, port = rest.partition("/")
    if head == "rout" and _bus_source(name):
        return name, None                    # plan 36 T1: All outputs' bus pin
    kind = kind_of(name)
    if head == "rout" and kind == "cloud":
        return name, None                    # plan 36 T2: a cloud's wire is the rig's
    if kind in (CAMERA, "cloud"):
        return None, NOT_REMOVABLE.format(label=label_of(name))
    if kind is None:
        return None, f"no node {name!r}"
    if head == "rin":
        return f"{name}.{port}", None
    return name, None


# plan 35 G: the picker's groups, by an item's kind, drawn in this order
# (ui_graph.render_picker; plan 36 T5: the starters first, in their own ▸)
PICKER_GROUP: dict[str, str] = {
    "starter": "starters",
    "scene": "scene", "shape": "scene", "hands": "scene", "layer": "scene", "guide": "scene",
    "backdrop": "scene",
    "lookback": "look-back", "echo": "look-back", "dream": "look-back",
    "pattern": "pictures", "composite": "pictures", "switch": "pictures",
    "channels": "pictures", "resize": "pictures", "delay": "pictures",
    "effect": "effects",
    "copy": "copy of",
}
PICKER_GROUPS = tuple(dict.fromkeys(PICKER_GROUP.values()))
# the frame kinds the picker adds once each (a second add says so): drawn
# disabled while the section has one
ONCE = ("scene", "shape", "backdrop", "pattern", "lookback")


def _echo_label(k: int) -> str:
    """Plan 34's look-back frame item: "echo.1 (newest)" … "echo.32 (oldest)"."""
    if k == 1:
        return "echo.1 (newest)"
    return f"echo.{k} (oldest)" if k == rgraph.MAX_ECHOES else f"echo.{k}"


def picker(edit: Edit) -> list[tuple[str, str | None, str]]:
    """The right-click picker's list (plan 35 G): (kind, file, label), in
    the owner's groups (`PICKER_GROUP`) — starters ▸ (plan 36 T5,
    `STARTERS`: each item's file its key); scene ▸ (the
    scene, the shape, hands, a hands layer, a hands guide, the backdrop);
    look-back ▸ (the look-back, plan 34's look-back frames echo.1 … echo.32
    and the dream); pictures ▸ (the faces pattern, a composite, a switch,
    R28's switch over the channels, plan 34's resize and delay); every
    effect file this build has; and a copy of each effect instance in the
    section."""
    gs = edit.graph
    files = gs.files() if gs is not None and hasattr(gs, "files") else None
    spec = _spec(edit)
    out: list[tuple[str, str | None, str]] = [("starter", k, w) for k, w in STARTERS]
    out += [("scene", None, "scene"), ("shape", None, "shape"), ("hands", None, "hands"),
            ("layer", None, "hands layer"), ("guide", None, "hands guide"),
            ("backdrop", None, "backdrop")]
    out += [("lookback", None, "look-back"),
            *(("echo", str(k), _echo_label(k)) for k in range(1, rgraph.MAX_ECHOES + 1)),
            ("dream", None, "dream")]
    out += [("pattern", None, "faces pattern"), ("composite", None, "composite"),
            ("switch", None, "switch"),
            *(("channels", port, label) for port, label in CHANNEL_SWITCH_PORTS),
            ("resize", None, "resize"), ("delay", None, "delay")]
    out += [("effect", f, f) for f in sorted(files or ())]
    out += [("copy", name, f"copy of {name}") for name in _instances(spec)]
    return out


def picked(edit: Edit) -> set[str]:
    """The picker's items already in the section (drawn disabled, plan 35
    G): the frame kinds there are one of, each echo index, the dream — by
    their (kind, file) keys' names."""
    named = _named(_doc(edit))
    return {n for n in named if kind_of(n) in (*ONCE, "echo", "dream")}


def picked_name(kind: str, file: str | None) -> str:
    """The node a picker item adds once (`picked`'s names): a frame kind
    itself, `echo.<k>`, the dream; "" for an item there may be many of."""
    if kind in (*ONCE, "dream"):
        return kind
    if kind == "echo":
        return f"echo.{file}"
    return ""


def _instances(spec) -> list[str]:
    """The effect instances section `spec` holds (by an entry or a wire),
    sorted: what a copy may draw again."""
    return sorted(n for n in frame_names(spec) if kind_of(n) == "effect") if spec else []


# R28: the ports "switch over the channels" feeds, and their picker words
CHANNEL_SWITCH_PORTS = (("pattern.media", "faces media"), ("backdrop.image", "backdrop"))
CHANNEL_SWITCH_REFUSAL = "a switch over the channels goes into pattern.media or backdrop.image"


def _frame_doc(spec) -> dict:
    """The section a GRAPH edit starts from (plan 35 G): the landed wired
    frame. Plan 36 T3 (W3): with none landed (or one from before the wired
    frame, which never lands), the empty frame the renderer draws for none
    — an edit adds what it lands and nothing else."""
    if spec is not None and getattr(spec, "wired", False):
        return spec.to_json()
    return rgraph.read_graph({rgraph.FRAME_KEY: rgraph.WIRED_FRAME}).to_json()


def _doc(edit: Edit) -> dict:
    return _with_frame(copy.deepcopy(_frame_doc(getattr(edit.graph, "spec", None))))


def _spec(edit: Edit):
    """The wired frame the page edits, read."""
    spec = getattr(edit.graph, "spec", None)
    if spec is not None and getattr(spec, "wired", False):
        return spec
    gs = edit.graph
    files = gs.files() if gs is not None and hasattr(gs, "files") else None
    try:
        return rgraph.read_graph(_doc(edit), effects=files)
    except rgraph.GraphError:
        return None


def _with_frame(doc: dict) -> dict:
    """`doc` given the wired frame's marker, first (plan 35 F: `"frame":
    "wired"`), and its nodes list — what every edit lands (`_with_run`'s
    successor: there is no run to give it)."""
    if doc.get(rgraph.FRAME_KEY) != rgraph.WIRED_FRAME or next(iter(doc), None) != rgraph.FRAME_KEY:
        rest = {k: v for k, v in doc.items() if k != rgraph.FRAME_KEY}
        doc.clear()
        doc[rgraph.FRAME_KEY] = rgraph.WIRED_FRAME
        doc.update(rest)
    doc.setdefault("nodes", [])
    return doc


def _frame_order(wires: list[dict]) -> list[dict]:
    """`wires` in the order a load writes a wired frame (the global
    constraints' canonical frame order, `graphmigrate.frame_wires`): the
    section's own wires first, as they stand, then the frame's — the
    scene's geometry, `backdrop.scene`, the look-back laid on (plan 36 T4:
    its occluder, the "add" composite and the dream feeding it), the run,
    All outputs' picture, hands and guide, the recorded picture's composite
    and the look-back's record (`lookback.image`, where the capture was). A
    stable sort: only `scene.geometry` takes several wires, and theirs keep
    their order (it is the draw order). So an edit that brings a frame back
    to a migrated one is that frame again, and the preset is clean."""
    into = {x["to"]: x["from"] for x in wires}
    run: list[str] = []
    head = into.get(f"{rgraph.ALL_OUTPUTS}.image")
    while kind_of(head) == "effect" and head not in run:
        run.insert(0, head)
        head = into.get(f"{head}.image")
    chain = (set(zip([head, *run], [f"{e}.image" for e in run]))
             if head is not None and run else set())
    held = into.get("lookback.image")
    comp = held if kind_of(held) == "composite" else None
    # (the composite laying the trail on: its `over` the look-back or a dream of it)
    lays = {x["to"].rpartition(".")[0] for x in wires
            if x["from"] in ("lookback", "dream") and x["to"].endswith(".over")
            and kind_of(x["to"].rpartition(".")[0]) == "composite"}
    groups = {"scene.geometry": 1, "backdrop.scene": 2, "lookback.occluder": 3,
              "dream.image": 3, f"{rgraph.ALL_OUTPUTS}.image": 6,
              f"{rgraph.ALL_OUTPUTS}.hands": 7, f"{rgraph.ALL_OUTPUTS}.guide": 8,
              "lookback.image": 10}

    def group(x: dict) -> int:
        if (x["from"], x["to"]) in chain:
            return 5
        if _drawn_edge(x):
            return 11
        node = x["to"].rpartition(".")[0]
        if node in lays and node != comp:
            return 3
        if comp is not None and node == comp:
            return 9
        return groups.get(x["to"], 0)
    return sorted(wires, key=group)


def _drawn_edge(x: dict) -> bool:
    """Whether wire `x` is one of the hidden edges' wires (plan 36 T2,
    `graphmigrate.drawn_edges`, written last in that order): the faces'
    pattern, the look-back's cover, a layer's or a guide's hands, a depth."""
    src, dst = x["from"], x["to"]
    node, _, port = dst.rpartition(".")
    return ((src, dst) == ("pattern", "shape.faces")
            or (src, dst) == (graphmigrate.COVER_PIN, "lookback.cover")
            or (src == graphmigrate.DEPTH_PIN and port == rgraph.DEPTH_PORT)
            or (port == "hands" and kind_of(node) in ("layer", "guide")
                and kind_of(src) == "hands"))


def _rig(edit: Edit) -> rgraph.RigWires:
    """The rig's own wires the open show holds (`edit.show`, plan 36 T1);
    with no show, the rig as it ships."""
    return rgraph.rig_of(getattr(edit, "show", None))


def _bus_source(name: str | None) -> bool:
    """Whether `name` is one of All outputs' bus pins (`output.all.image` …)."""
    head, _, port = (name or "").rpartition(".")
    return head == rgraph.ALL_OUTPUTS and port in rgraph.BUS_PORTS


def _land(edit: Edit, doc: dict, label: str, said: str, dry: bool = False,
          rig: rgraph.RigWires | None = None) -> str | None:
    """Read `doc` back as a preset would (a note is the refusal, nothing
    changed); else, unless `dry`, the undo step and the landing. `rig`
    (plan 36 T1): the show's rig wires after the edit, set in the same
    undo step — refused with no show to hold them."""
    if rig is not None and rig != _rig(edit) and getattr(edit, "show", None) is None:
        return BUS_NO_SHOW
    gs = edit.graph
    if gs is None:
        return "no preset is loaded"
    files = gs.files() if hasattr(gs, "files") else None
    _with_frame(doc)
    # a frame node's bare entry is only what keeps it unwired (`_keep_declared`):
    # once a wire names it again, the wire says it
    wired = {n for x in doc.get("wires", []) for n in (x["from"], x["to"].rpartition(".")[0])}
    doc["nodes"] = [e for e in doc["nodes"] if not (
        e.get("kind") in rgraph.FRAME_KINDS and set(e) <= {"kind", "instance"}
        and _node_name(e) in wired)]
    doc["wires"] = _frame_order(doc.get("wires", []))
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
    same = new == _doc(edit) and getattr(edit.graph, "spec", None) is not None
    if same and (rig is None or rig == _rig(edit)):
        edit.said = "already so"
        return None
    if edit.push is not None:
        edit.push(label)
    if not same:
        gs.land(spec, new)
    if rig is not None and rig != _rig(edit):
        edit.show.rig = rig
    edit.said = said
    return None


def _entry_name(e: dict) -> str | None:
    if e.get("kind") != "effect" or "file" not in e:
        return None
    return rgraph.instance_name(e["file"], e.get("instance", 1))


def _node_name(e: dict) -> str | None:
    """The node a section entry declares, by its name (plan 35 F's kinds too)."""
    kind, n = e.get("kind"), e.get("instance", 1)
    if not isinstance(n, int):
        return None
    if kind == "effect":
        return _entry_name(e)
    if kind == "hands":
        return rgraph.wired_hands_name(n)
    if kind in ("layer", "guide"):
        return f"{rgraph.wired_hands_name(n)}.{kind}"
    if kind == "echo":
        return f"echo.{e.get('index')}"
    if kind in rgraph.FRAME_KINDS or kind == "dream":
        return kind
    if kind in ("composite", "switch", "delay", "resize", "copy"):
        return kind if n == 1 else f"{kind}.{n}"
    return None


def _named(doc: dict) -> set[str]:
    """Every name section `doc` says: its entries' and its wires' ends."""
    out = {x for x in map(_node_name, doc.get("nodes", [])) if x}
    for x in doc.get("wires", []):
        out |= {rgraph.pin_node(x["from"]) or x["from"], x["to"].rpartition(".")[0]}
    return out


def _keep_declared(doc: dict, names: Iterable[str]) -> None:
    """Each frame node of `names` that the section no longer names (its last
    wire just went) kept by its entry — a node unwired stays on the canvas,
    faint ("reaches nothing"), to wire on or delete (plan 35 G); an
    instance-1 effect by R21's entry. A hands node, a channel, a declared
    kind keep theirs or need none."""
    named = _named(doc)
    # (plan 36 T2: a pin is its node's name: `scene.cover` names the scene)
    for name in dict.fromkeys(rgraph.pin_node(n) or n for n in names):
        if name in named:
            continue
        kind = kind_of(name)
        if kind in ("layer", "guide"):
            n = rgraph.split_instance(rgraph.hands_of(name))[1]
            doc["nodes"].append({"kind": kind, **({"instance": n} if n != 1 else {})})
        elif kind in rgraph.FRAME_KINDS:
            doc["nodes"].append({"kind": kind})
        elif kind == "effect" and rgraph.split_instance(name)[1] == 1:
            doc["nodes"].append({"kind": "effect", "file": name})
        named.add(name)


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


def render_wire(edit: Edit, src: str, dst: str, dry: bool = False,
                doc: dict | None = None) -> str | None:
    """A wire `src → dst` into the section (the one into `dst` replaced,
    but a `scene.geometry`'s, which takes several) — that one wire and
    nothing else (plan 36 T1: no placement, switch or other wire moves
    with it; a placement it would contradict is refused in words by the
    read). From one of All outputs' bus pins it is the rig's cable into
    the window's same port (`bus_wire`): the show's, joined, and the
    preset's own wire into that port, if any, gives the port up to it.
    `doc` (plan 35 T6): the section to wire on, else the landed one."""
    s, why = spec_name(src, edit.render)
    if s is None:
        return why
    d, why = spec_name(dst, edit.render)
    if d is None:
        return why
    if kind_of(d) is not None:
        return f"{d} is a node, not a port: a wire goes into {rgraph.WIRED_TO_WORDS}"
    w = rgraph.Wire(s, d)
    doc = _doc(edit) if doc is None else doc
    if kind_of(s) == "cloud":
        # plan 36 T2: a cloud's one wire is the rig's, into the scene
        if not rgraph.is_cloud_wire(w):
            return CLOUD_INTO_SCENE.format(cloud=s)
        if getattr(edit, "show", None) is None:
            return BUS_NO_SHOW
        return _land(edit, doc, f"wire {w}", f"wired {w}", dry, rig=_rig(edit).joining(w))
    if _bus_source(s):
        if not rgraph.is_bus(w):
            return BUS_SAME_PORT.format(port=s.rpartition(".")[2])
        if getattr(edit, "show", None) is None:
            return BUS_NO_SHOW
        gone = [x for x in doc.get("wires", []) if x["to"] == d]
        doc["wires"] = [x for x in doc.get("wires", []) if x["to"] != d]
        _keep_declared(doc, [x["from"] for x in gone])
        return _land(edit, doc, f"wire {w}", f"wired {w}", dry, rig=_rig(edit).joining(w))
    wires = doc.get("wires", [])
    if d in rgraph.MANY_PORTS:
        # several wires go in, drawn in section order — a hands node's
        # before the shape's, the order the frame is written in (plan 35 F)
        keep = [x for x in wires if (x["from"], x["to"]) != (s, d)]
        at = next((i for i, x in enumerate(keep) if x["to"] == d and x["from"] == "shape"),
                  len(keep)) if kind_of(s) == "hands" else len(keep)
        doc["wires"] = [*keep[:at], w.to_json(), *keep[at:]]
    else:
        doc["wires"] = [x for x in wires if x["to"] != d] + [w.to_json()]
    # (plan 36 T1: D1's placements stay where they are — the drag lands one wire)
    gone = {x["from"] for x in wires if x["to"] == d and x not in doc["wires"]}
    _keep_declared(doc, gone)
    return _land(edit, doc, f"wire {w}", f"wired {w}", dry)


def render_unwire(edit: Edit, cable, dst: str | None = None) -> str | None:
    """Plan 35 G: any wire of the section goes — the run's, the look-back's,
    the scene's geometry, a window's — and a frame node it was the last
    mention of is kept by its entry (`_keep_declared`), drawn faint. The one
    refusal left is a wire the section does not have."""
    s: str | None
    if isinstance(cable, VCable) and isinstance(cable.ref, rgraph.Wire):
        s, d = cable.ref.src, cable.ref.dst
        if rgraph.is_rig(cable.ref):
            return _cut_bus(edit, cable.ref)
    else:
        if isinstance(cable, VCable):
            src, dst = cable.src_port, cable.dst_port
        else:
            src = cable
        s, why = spec_name(src, edit.render)
        if s is None:
            return why
        if dst is not None:
            d, why = spec_name(dst, edit.render)
            if d is None:
                return why
        else:                                # a port's name alone: whatever is wired into it
            s, d = None, s
        if s is not None and rgraph.is_rig(rgraph.Wire(s, d)):
            return _cut_bus(edit, rgraph.Wire(s, d))
    doc = _doc(edit)
    wires = doc.get("wires", [])
    left = [x for x in wires if not (x["to"] == d and (s is None or x["from"] == s))]
    gone = [x for x in wires if x not in left]
    doc["wires"] = left
    if not gone and s is not None:
        before = copy.deepcopy(doc["nodes"])

        def placed_here(name: str, key: str, where: str) -> bool:
            if key == "after" and not where.startswith("output."):
                return where == s and d == f"{name}.image"
            return name == s and d == f"{where}.image"
        _unplace(doc, placed_here)
        if doc["nodes"] == before:
            return NO_SUCH_WIRE.format(wire=f"{s} → {d}")
    elif not gone:
        # (plan 36 T1: a window's port with no wire of the preset's: its
        # one cable is the rig's bus cable, if it stands)
        port = rgraph.Wire(f"{rgraph.ALL_OUTPUTS}.{d.rpartition('.')[2]}", d)
        if rgraph.is_bus(port) and _rig(edit).has(port):
            return _cut_bus(edit, port)
        return NO_SUCH_WIRE.format(wire=f"→ {d}")
    _keep_declared(doc, [n for x in gone for n in (x["from"], x["to"].rpartition(".")[0])])
    said = f"{s} → {d}" if s is not None else d
    return _land(edit, doc, f"unwire {d}", f"unwired {said}")


def _cut_bus(edit: Edit, w: rgraph.Wire) -> str | None:
    """Plan 36 T1: the rig's bus cable `w` cut in the open show — one undo
    step, the preset untouched; the window shows nothing on that port
    until the cable is joined again or the preset wires the port. Plan 36
    T2: and a cloud's wire into the scene (`graph.is_rig`), the same way."""
    rig = _rig(edit)
    if not rig.has(w):
        return NO_SUCH_WIRE.format(wire=str(w))
    return _land(edit, _doc(edit), f"cut {w}", f"cut the rig's cable {w}", rig=rig.cutting(w))


def _new_instance(spec, file: str) -> int:
    """The instance of effect `file` an add or an insert makes (R25): 1,
    the file itself, when no wire, node entry or placement in section
    `spec` holds it, else the lowest instance none holds."""
    held: set[int] = set()
    for e in (spec.effects if spec is not None else ()):
        if e.file == file:
            held.add(e.n)
    for w in (spec.all_wires() if spec is not None else ()):
        for end in (w.src, w.node):
            if kind_of(end) == "effect":
                f, n = rgraph.split_instance(end)
                if f == file:
                    held.add(n)
    return next(n for n in range(1, len(held) + 2) if n not in held)


def _switch_on(edit: Edit, name: str) -> None:
    """R25: effect `name`, just added or inserted, switched on
    (`fx.<name>.on`) — after the landing that declared its params and in
    the same undo step (the step `_land` pushed is still open this frame,
    so an undo puts the value back with the graph). Nothing to do with no
    registry to hand (a stand-in section) or no such param."""
    reg = getattr(edit.graph, "reg", None) or edit.reg
    pid = f"fx.{name}.on"
    if reg is not None and pid in reg:
        reg[pid].set(True)


def _effect_entry(file: str, n: int) -> dict:
    """A section's entry for an unwired effect `file`'s instance `n`
    (instance 1: no instance key, R21's form)."""
    return {"kind": "effect", "file": file, **({"instance": n} if n != 1 else {})}


# what each frame node added from the picker says next (plan 35 G)
ADDED = {
    "scene": "wire geometry into scene.geometry, and the scene into a picture port",
    "shape": "wire it into scene.geometry",
    "backdrop": "wire a picture into backdrop.image and the scene into backdrop.scene",
    "pattern": "the shape's faces show it while nothing is wired into shape.faces",
    "lookback": ("wire what it records into lookback.image, and its trail into a "
                 "composite's over (add) — its echo.1 … pins are its frames"),
    "layer": "wire it into an output's hands or a composite's over",
    "guide": "wire it into an output's guide",
}


def _ordinal(k: int) -> str:
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def _next(spec, kind: str) -> int:
    """The next instance of a declared kind (`composite`, `switch`, `delay`,
    `resize`, `copy`) in section `spec`: one past the highest."""
    return max([got.n for k, got in (spec.others if spec is not None else ()) if k == kind],
               default=0) + 1


def render_add(edit: Edit, kind: str, file: str | None = None, **settings) -> str | None:
    edit.placed = ()
    if kind == "starter":
        return render_starter(edit, file or "scene")
    spec = _spec(edit)
    doc = _with_frame(_doc(edit))
    named = _named(doc)
    if kind in ONCE:
        label = label_of(kind)
        if kind in named:
            return IN_ALREADY.format(label=label)
        doc["nodes"].append({"kind": kind})
        edit.added = kind
        return _land(edit, doc, f"add {kind}", f"{label} added: {ADDED[kind]}")
    if kind in ("layer", "guide"):
        held = sorted({1} | {h.n for h in (spec.hands if spec is not None else ())})
        n = settings.get("instance") or next(
            (k for k in held if f"{rgraph.wired_hands_name(k)}.{kind}" not in named), None)
        if n is None or f"{rgraph.wired_hands_name(n)}.{kind}" in named:
            return IN_ALREADY.format(label=label_of(f"{rgraph.wired_hands_name(n or 1)}.{kind}"))
        name = edit.added = f"{rgraph.wired_hands_name(n)}.{kind}"
        doc["nodes"].append({"kind": kind, **({"instance": n} if n != 1 else {})})
        return _land(edit, doc, f"add {name}", f"{label_of(name)} added: {ADDED[kind]}")
    if kind == "hands":
        draw = ({"draw": settings["draw"]} if settings.get("draw", "solid") != "solid" else {})
        if not {"hands", "hands.layer", "hands.guide"} & named:
            # hands 1, every frame's: drawn in the scene where there is one,
            # else as its layer — a hands node with neither is drawn nowhere
            edit.added = "hands"
            if "scene" in named:
                doc["wires"] = [*doc.get("wires", []), {"from": "hands", "to": "scene.geometry"}]
                said = "Hands added, drawn in the scene"
            else:
                doc["nodes"].append({"kind": "layer"})
                said = "Hands added, drawn alone as its layer: wire Hands layer into a picture port"
            if draw:
                doc["nodes"].insert(0, {"kind": "hands", **draw})
            return _land(edit, doc, "add hands", said)
        held = {h.n for h in (spec.hands if spec is not None else ())} | {1}
        n = max(held) + 1
        doc["nodes"].append({"kind": "hands", "instance": n, **draw})
        name = edit.added = rgraph.wired_hands_name(n)
        return _land(edit, doc, f"add {name}", f"{label_of(name)} added: wire it into "
                                               "scene.geometry, or add its layer")
    if kind == "effect":
        files = edit.graph.files() if hasattr(edit.graph, "files") else None
        if not file or (files is not None and file not in files):
            return f"no {file} effect in this build"
        n = _new_instance(spec, file)
        doc["nodes"].append(_effect_entry(file, n))
        name = edit.added = rgraph.instance_name(file, n)
        # plan 33 U: on no wire — it reaches nothing until it is wired in;
        # R25: switched on, so wiring it in shows it
        why = _land(edit, doc, f"add {name}", f"{name} added: its params are fx.{name}.*")
        if why is None:
            _switch_on(edit, name)
        return why
    if kind == "copy":
        if not file or file not in _instances(spec):
            return NO_SUCH_COPY.format(of=file)
        c = rgraph.CopyAt(_next(spec, "copy"), file)
        doc["nodes"].append(c.to_json())
        edit.added = c.name
        return _land(edit, doc, f"add {c.name}",
                     f"{label_of(c.name, of=file)} added: wire a picture into {c.name}.image "
                     f"— it draws {file} again there, with its knobs")
    if kind == "switch":
        sw = rgraph.SwitchAt(_next(spec, "switch"))
        doc["nodes"].append(sw.to_json())
        edit.added = sw.name
        return _land(edit, doc, f"add {sw.name}",
                     f"{sw.name} added: wire pictures into in1 … in8, pick one with "
                     f"{sw.name}.select")
    if kind == "composite":
        c = rgraph.CompositeAt(_next(spec, "composite"), settings.get("blend", "over"))
        edit.added = c.name
        doc["nodes"].append(c.to_json())
        return _land(edit, doc, f"add {c.name}", f"{c.name} added: wire its under and over")
    if kind in ("delay", "resize"):
        at = (rgraph.DelayAt if kind == "delay" else rgraph.ResizeAt)(_next(spec, kind))
        doc["nodes"].append(at.to_json())
        name = edit.added = at.name
        how = ("its picture is that one, a frame late" if kind == "delay"
               else f"it makes it at {name}.size")
        return _land(edit, doc, f"add {name}",
                     f"{name} added: wire a picture into {name}.image — {how}")
    if kind == "echo":
        # plan 36 T4: an echo is the look-back's own output — its pin; the
        # item adds the look-back when the section has none
        try:
            k = int(file or 1)
        except ValueError:
            return f"echo {file!r}: an index from 1 to {rgraph.MAX_ECHOES}"
        pin = f"lookback.echo.{k}"
        if "lookback" in named:
            edit.added = "lookback"
            edit.said = (f"{pin} is the look-back's {_ordinal(k)} newest frame — wire it from "
                         "its pin into a picture port")
            return None
        doc["nodes"].append({"kind": "lookback"})
        edit.added = "lookback"
        return _land(edit, doc, "add lookback", f"lookback added: {pin} is its {_ordinal(k)} "
                                                "newest frame — wire it from its pin")
    if kind == "dream":
        if "dream" in named:
            return IN_ALREADY.format(label=label_of("dream"))
        doc["nodes"].append({"kind": "dream"})
        edit.added = "dream"
        return _land(edit, doc, "add dream", "dream added: wire a picture into dream.image, "
                                             "and the dream into a composite's over — "
                                             "dream.on turns it on")
    return f"no node kind {kind!r}: the picker adds what its groups list"


def render_starter(edit: Edit, which: str = "scene", cable=None) -> str | None:
    """A starter (plan 36 T5, W5; plan 35 G's "scene starter" the first):
    its pre-wired group in one landing — one undo step — every node and
    cable ordinary after it. `edit.placed` is what it added, left to right
    (a node already in the section, a channel, All outputs stay where they
    sit: the page places only these).

    - **scene**: `shape → scene.geometry`, `scene → output.all.image` (in
      place of whatever fed All outputs; the shape and the scene kept when
      the section has them) — plain faces, no pattern wire.
    - **tracers**: the look-back recording the picture, laid on it by a
      new composite (blend add, `graphmigrate.split_lookback`'s): `picture
      → lookback.image`, `→ lookback.occluder`, `→ composite.under`,
      `lookback → composite.over`, the composite where the picture went.
    - **tracers+dream**: the same with `lookback → dream.image`, `dream →
      composite.over`.
    - **dream**: `picture → dream.image`, `→ composite.under`, `dream →
      composite.over` (blend over: the dream is its picture, dreamed).
    - **backdrop**: a backdrop, `channel.a → backdrop.image`.

    The picture is `cable`'s source and the composite goes where the cable
    went; with no cable, the scene, the composite into the one picture
    port the scene feeds. Where that is not one thing (no scene; the scene
    feeding no picture port, or several) the starter wires what it can and
    the words name what is left unwired — it never guesses. A look-back,
    a dream or a backdrop already in the section is refused in words (one
    of each: one live dream, D2)."""
    edit.placed = ()
    label = dict(STARTERS).get(which)
    if label is None:
        return NO_STARTER.format(which=which)
    src = dst = None
    if cable is not None:
        if which not in CABLE_STARTERS:
            return NO_CABLE_STARTER.format(label=label)
        src, dst, why = _cable_ends(edit, cable)
        if why is not None:
            return why
    doc = _with_frame(_doc(edit))
    before = _named(doc)
    if which == "scene":
        wires = [x for x in doc.get("wires", []) if x["to"] != f"{rgraph.ALL_OUTPUTS}.image"]
        for a, b in SCENE_CHAIN:
            if {"from": a, "to": b} not in wires:
                wires.append({"from": a, "to": b})
        doc["wires"] = wires
        return _started(edit, doc, before, "shape", "scene", label=label, said=STARTER_SAID)
    if which == "backdrop":
        if "backdrop" in before:
            return IN_ALREADY.format(label=label_of("backdrop"))
        feed = rgraph.channel_name(rgraph.MEDIA_CHANNELS[0])
        doc["nodes"].append({"kind": "backdrop"})
        doc["wires"] = [*doc.get("wires", []), {"from": feed, "to": "backdrop.image"}]
        return _started(edit, doc, before, "backdrop", label=label,
                        said=f"{label}: {feed} → backdrop.image — left unwired: backdrop.scene "
                             "and the backdrop's picture (wire it into a picture port)")
    looks = which in ("tracers", "tracers+dream")
    dreams = which in ("tracers+dream", "dream")
    for kind, wanted in (("lookback", looks), ("dream", dreams)):
        if wanted and kind in before:
            return IN_ALREADY.format(label=label_of(kind))
    unwired: list[str] = []
    if cable is None:
        src = "scene" if "scene" in before else None
        feeds = [x["to"] for x in doc.get("wires", []) if src and x["from"] == src
                 and _picture_port(x["to"])]
        dst = feeds[0] if len(feeds) == 1 else None
        if src is not None and dst is None:
            unwired.append("the composite's picture (the scene feeds "
                           + ("no picture port" if not feeds else f"{len(feeds)} ports") + ")")
    comp = rgraph.CompositeAt(_next(_spec(edit), "composite"), "add" if looks else "over")
    wires = list(doc.get("wires", []))
    if dst is not None:     # (what fed picture port `dst` — one wire: the composite does now)
        wires = [x for x in wires if x["to"] != dst]
    head = "lookback" if looks else "dream"
    new = [("lookback", "dream.image")] if which == "tracers+dream" else []
    new.append(("dream" if dreams else "lookback", f"{comp.name}.over"))
    ins = ([f"{head}.image"] + (["lookback.occluder"] if looks else []) + [f"{comp.name}.under"])
    if src is not None:
        new = [(src, p) for p in ins] + new
    else:
        unwired.insert(0, ", ".join(ins) + " (no scene: wire a picture into them)")
    if dst is not None:
        new.append((comp.name, dst))
    elif src is None:
        unwired.append("the composite's picture")
    doc["wires"] = wires + [{"from": a, "to": b} for a, b in new]
    for kind, wanted in (("lookback", looks), ("dream", dreams)):
        if wanted:
            doc["nodes"].append({"kind": kind})
    doc["nodes"].append(comp.to_json())
    chain = " → ".join([*(["lookback"] if looks else []), *(["dream"] if dreams else []),
                        comp.name])
    said = (f"{label}: {chain}" + (f" over {src}" if src else "")
            + (f" → {dst}" if dst else "")
            + (" — left unwired: " + "; ".join(unwired) if unwired else ""))
    order = (*(["lookback"] if looks else []), *(["dream"] if dreams else []), comp.name)
    return _started(edit, doc, before, *order, label=label, said=said)


def _picture_port(port: str) -> bool:
    """Whether `port` (`node.port`) takes a picture (not a depth, not geometry)."""
    node, _, p = port.rpartition(".")
    return _takes(kind_of(node)).get(p) == IMAGE and p != rgraph.DEPTH_PORT


def _started(edit: Edit, doc: dict, before: set[str], *order: str, label: str,
             said: str) -> str | None:
    """Land a starter's `doc` (one undo step, named for its `label`); on a
    landing, `edit.placed` the names of `order` the section did not have
    before (`before`) — what the page lays out left to right."""
    why = _land(edit, doc, f"starter: {label}", said)
    if why is None and edit.said != "already so":
        after = _named(_doc(edit))
        edit.placed = tuple(n for n in order if n in after and n not in before)
    return why


def render_channel_switch(edit: Edit, port: str) -> str | None:
    """R28: a new switch over the eight channels into `port`
    (`pattern.media` or `backdrop.image`) in one landing — `channel.a … h →
    in1 … in8`, the switch into the port in place of whatever fed it — and
    its `select` the channel that fed the port (through a switch already
    there, at that switch's pick), else 1, in the same undo step: headline
    use 3 (a knob picks the faces' channel) in one gesture, the same wires
    a driven `view.media` migrates to (row 350)."""
    if port not in dict(CHANNEL_SWITCH_PORTS):
        return CHANNEL_SWITCH_REFUSAL
    spec = _spec(edit)
    reg = getattr(edit.graph, "reg", None) or edit.reg
    selects: dict[str, int] = {}
    for sw in (spec.switches if spec is not None else ()):
        pid = f"{sw.name}.select"
        if reg is not None and pid in reg:
            selects[sw.name] = reg[pid].value
    ch = rgraph.channel_into(spec.wires if spec is not None else (), port, selects)
    k = rgraph.MEDIA_CHANNELS.index(ch) + 1 if ch and ch in rgraph.MEDIA_CHANNELS else 1
    sw = rgraph.SwitchAt(_next(spec, "switch"))
    doc = _with_frame(_doc(edit))
    doc["nodes"].append(sw.to_json())
    doc["wires"] = [x for x in doc.get("wires", []) if x["to"] != port] + [
        {"from": rgraph.channel_name(c), "to": f"{sw.name}.in{i}"}
        for i, c in enumerate(rgraph.MEDIA_CHANNELS, 1)] + [{"from": sw.name, "to": port}]
    why = _land(edit, doc, f"switch over the channels into {port}",
                f"{sw.name} over channels a … h into {port}, at {rgraph.MEDIA_CHANNELS[k - 1]}")
    if why is None:
        edit.added = sw.name
        pid = f"{sw.name}.select"
        if reg is not None and pid in reg:
            reg[pid].set(k)
    return why


def _touches(x: dict, names: set[str]) -> bool:
    # (plan 36 T2: a wire from a node's pin — `scene.cover` — touches the node)
    return (x["from"] in names or rgraph.pin_node(x["from"]) in names
            or x["to"].rpartition(".")[0] in names)


# ---- plan 33 U: effects onto picture cables, out of their place ----

def _lift(doc: dict, name: str) -> None:
    """Effect (or copy) `name` out of where its picture goes, in section
    `doc`: the wire into its `image` port and every wire out of it gone,
    and what fed it wired on into each port it fed — the chain closed over
    it. A wire into its `aux` stays; a D1 placement of it goes; (R21) an
    instance-1 effect left on no wire stays named, unreached. With nothing
    wired in, its wires out simply go."""
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
    if kind_of(name) == "effect" and n == 1 and not any(_touches(x, {name}) for x in keep) \
            and not any(_entry_name(e) == name for e in doc.get("nodes", [])):
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
    wires = doc.get("wires", [])
    if d in rgraph.MANY_PORTS:
        kept = [x for x in wires if (x["from"], x["to"]) != (s, d)]
    else:
        kept = [x for x in wires if x["to"] != d]
    doc["wires"] = kept + [{"from": s, "to": f"{name}.image"}, {"from": name, "to": d}]


def _cable_ends(edit: Edit, cable) -> tuple[str | None, str | None, str | None]:
    """A picture cable as the section names it: (`src`, `dst port`, None),
    or (None, None, why not). `cable` is a `VCable` (its wire, else its
    pins) or its two ends — canvas pins, or the section's names."""
    if isinstance(cable, VCable) and isinstance(cable.ref, rgraph.Wire):
        s, d = cable.ref.src, cable.ref.dst
    else:
        a, b = (cable.src_port, cable.dst_port) if isinstance(cable, VCable) else cable
        s, why = spec_name(a, edit.render)
        if s is None:
            return None, None, why
        d, why = spec_name(b, edit.render)
        if d is None:
            return None, None, why
    if _bus_source(s):                      # plan 36 T1: the rig's, not the preset's
        return None, None, BUS_NO_EFFECT.format(wire=f"{s} → {d}")
    if kind_of(d) is not None:
        return None, None, f"{d} is a node, not a port: a wire goes into {rgraph.WIRED_TO_WORDS}"
    w = rgraph.Wire(s, d)
    if (_takes(kind_of(w.node)).get(w.port) != IMAGE or _makes(kind_of(s)) != IMAGE
            or rgraph.pin_node(s) is not None or w.port == rgraph.DEPTH_PORT):
        # (plan 36 T2: nor the scene's depth — a depth, not a picture)
        return None, None, f"{w} is no picture cable: an effect goes onto a picture"
    return s, d, None


def render_insert(edit: Edit, cable, file: str) -> str | None:
    s, d, why = _cable_ends(edit, cable)
    if why is not None:
        return why
    files = edit.graph.files() if hasattr(edit.graph, "files") else None
    if not file or (files is not None and file not in files):
        return f"no {file} effect in this build"
    spec = _spec(edit)
    n = _new_instance(spec, file)                   # R25: the file itself when none holds it
    name = rgraph.instance_name(file, n)
    doc = _doc(edit)
    if n != 1:                                      # (instance 1 is named by its wires)
        doc["nodes"].append(_effect_entry(file, n))
    _onto(doc, s, d, name)
    why = _land(edit, doc, f"insert {name} into {s} → {d}", f"{name} inserted: {s} → {name} → {d}")
    if why is None:
        edit.added = name
        _switch_on(edit, name)                      # R25: shown on the first gesture
    return why


def render_place(edit: Edit, cable, name: str) -> str | None:
    s, d, why = _cable_ends(edit, cable)
    if why is not None:
        return why
    nm, why = spec_name(name, edit.render)
    if nm is None:
        return why
    if kind_of(nm) not in ("effect", "copy"):
        return f"{nm} is no effect: an effect goes onto a picture cable"
    if s == nm or rgraph.Wire(s, d).node == nm:
        return f"{nm} is on that cable already"
    doc = _doc(edit)
    _lift(doc, nm)
    _onto(doc, s, d, nm)
    return _land(edit, doc, f"move {nm} onto {s} → {d}", f"{nm} moved: {s} → {nm} → {d}")


def render_drop(edit: Edit, node: str) -> str | None:
    """Plan 35 G: any node of the section goes — its entry and every wire
    touching it, one undo step (an effect or a copy lifted first, so the
    chain closes over it; a hands node with its layer and its guide, its
    params kept in the registry; R16, an effect with its copies; R18, the
    backdrop like an effect — what its `scene` port took goes on to what it
    fed, and the note says so). A window
    is the rig's: its wires go, and it shows its ground (`OUTPUT_UNWIRED`,
    said, no refusal; with none, `NOTHING_TO_DELETE`); All outputs the
    same. The camera and a cloud are the rig's (`spec_name`)."""
    name, why = spec_name(node, edit.render)
    if name is None:
        return why
    kind = kind_of(name)
    doc = _doc(edit)
    slots = getattr(edit, "slots", ())
    if kind in ("output", rgraph.ALL_OUTPUTS):
        said = (ALL_UNWIRED if kind == rgraph.ALL_OUTPUTS
                else OUTPUT_UNWIRED.format(label=label_of(name, slots)))
        wires = doc.get("wires", [])
        left = [x for x in wires if x["to"].rpartition(".")[0] != name]
        # plan 36 T1: a window's bus cables are wires into it too — cut
        # with the rest, in the same step, so it shows its ground
        # (only the drawn ones: a bus cable into a port the preset wires
        # itself is not drawn, and stays as it is — M2)
        rig = _rig(edit)
        owned = {x["to"] for x in wires}
        bus = [] if kind == rgraph.ALL_OUTPUTS or getattr(edit, "show", None) is None else [
            w for w in rig.present(rgraph.bus_wire(int(name.partition(".")[2]), p)
                                   for p in rgraph.BUS_PORTS) if w.dst not in owned]
        if len(left) == len(wires) and not bus:     # (T5 review: say nothing was done)
            edit.said = NOTHING_TO_DELETE.format(
                what="All outputs" if kind == rgraph.ALL_OUTPUTS
                else f"output {name.partition('.')[2]}")
            return None
        doc["wires"] = left
        _keep_declared(doc, [x["from"] for x in wires if x not in left])
        for w in bus:
            rig = rig.cutting(w)
        return _land(edit, doc, f"unwire {name}", said, rig=rig if bus else None)
    label = label_of(name, slots, of=next((c.of for c in getattr(_spec(edit), "copies", ())
                                           if c.name == name), ""))
    before = copy.deepcopy(doc)
    names = {name}
    if kind == "hands":
        names |= {f"{name}.layer", f"{name}.guide"}
    # R16: an effect's copies go with it (a copy of nothing is no node), in
    # the same landing — each lifted, so its chain closes over it too
    mine = ([_node_name(e) for e in doc.get("nodes", [])
             if e.get("kind") == "copy" and e.get("of") == name] if kind == "effect" else [])
    for x in ([name, *mine] if kind in ("effect", "copy") else ()):
        _lift(doc, x)
    names |= set(mine)
    # R18 (final review): the backdrop lifted as an effect is — the picture
    # into its `scene` port wired on into every port it fed, so deleting
    # it shows the scene, not black
    joined: list[dict] = []
    if kind == "backdrop":
        wires = doc.get("wires", [])
        under = next((x["from"] for x in wires if x["to"] == f"{name}.scene"), None)
        if under is not None:
            joined = [{"from": under, "to": x["to"]} for x in wires
                      if x["from"] == name and not _touches({"from": under, "to": x["to"]},
                                                            names)]
    doc["nodes"] = [e for e in doc.get("nodes", []) if _node_name(e) not in names]
    gone = [x for x in doc.get("wires", []) if _touches(x, names)]
    doc["wires"] = [x for x in doc.get("wires", []) if not _touches(x, names)]
    doc["wires"] += [x for x in joined if x not in doc["wires"]]
    _unplace(doc, lambda e, key, where: where in names)
    if doc == before:
        return f"{label} is not in the preset's graph"
    _keep_declared(doc, [n for x in gone for n in (x["from"], x["to"].rpartition(".")[0])
                         if n not in names])
    also = ("" if not mine else ", and its copy" if len(mine) == 1
            else f", and its {len(mine)} copies")
    if joined:
        what = "the scene" if joined[0]["from"] == "scene" else label_of(joined[0]["from"], slots)
        to = ", ".join(dict.fromkeys(label_of(x["to"].rpartition(".")[0], slots)
                                     for x in joined))
        also += f"; {what} goes on to {to}"
    return _land(edit, doc, f"delete {name}", f"{label} deleted{also}")


def render_set(edit: Edit, node: str, **settings) -> str | None:
    name, why = spec_name(node, edit.render)
    if name is None:
        return why
    kind = kind_of(name)
    doc = _doc(edit)
    if kind in ("hands", "layer", "guide"):
        hands = name if kind == "hands" else rgraph.hands_of(name)
        _, n = rgraph.split_instance(hands)
        if "into" in settings:
            return rgraph.INTO_IS_A_WIRE.format(hands=hands)
        e = _hands_entry(doc, n)
        if e is None:
            if n > 1:
                return f"no {hands} hands node in this graph"
            e = {"kind": "hands"}
            doc["nodes"].insert(0, e)
        how = settings.get("draw", "solid")
        if how == "solid":
            e.pop("draw", None)
        else:
            e["draw"] = how
        if len(e) == 1:
            doc["nodes"].remove(e)
        return _land(edit, doc, f"{hands} {how}", f"{label_of(hands)} drawn {how}")
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


# ---- plan 35 T6 (U): the OUTPUT and LOOKBACK pages as views of the wires.
# A page sets a picture port (a window's, All outputs', the look-back's
# capture) and a window's "hands through the effects" — each a GRAPH edit
# through `_land`: one undo step, GRAPH's refusals, and the frame in its
# canonical wire order, so an edit put back leaves the frame as it was.
# The mutes are the window's (row 374), never written here.

AS_ALL = "as All outputs"      # a window's picture port by the rig's bus cable (plan 36 T1)
NOTHING = "nothing"            # a window's: `ground` wired; All outputs', the capture: no wire
# the areas a page lists the graph's pictures in (the canvas's, left to right)
PICTURE_AREA: dict[str, str] = {
    "channel": MEDIA, "pattern": MEDIA, "switch": MEDIA, "delay": MEDIA,
    "scene": SCENE_AREA, "layer": SCENE_AREA, "guide": SCENE_AREA, "backdrop": SCENE_AREA,
    "lookback": LOOKBACK_AREA, "echo": LOOKBACK_AREA, "dream": LOOKBACK_AREA,
    "effect": EFFECTS_AREA, "copy": EFFECTS_AREA, "composite": EFFECTS_AREA,
    "resize": EFFECTS_AREA,
}
PICTURE_AREAS = (MEDIA, SCENE_AREA, LOOKBACK_AREA, EFFECTS_AREA)
THROUGH_NO_LAYER = ("hands through the effects: All outputs lays no hands layer over its "
                    "picture — wire a hands layer into output.all.hands on GRAPH")
THROUGH_OWN_PICTURE = ("{label} shows {src} by its own wire: the hands go through All "
                       "outputs' effects — set its picture to \"as All outputs\" first")
# plan 36 T1: a window whose picture cable from All outputs is cut shows no
# picture to put the hands through; one whose hands port the preset wires
# keeps that wire (the toggle never drops a wire it did not write)
THROUGH_NO_PICTURE = ("{label} shows no picture: its cable from All outputs is cut — "
                      "set its picture to \"as All outputs\" first")
THROUGH_OWN_HANDS = ("{label}'s hands port is wired ({src} → output.{n}.hands): through "
                     "puts the hands in its picture instead — unwire that port first")


def page_spec(spec):
    """The wired frame a page reads (plan 35 U): `spec` itself when it is
    one; else (no preset landed, a section from before the wired frame) the
    frame a GRAPH edit starts from (`_frame_doc`) read — None if it will
    not read."""
    if spec is not None and getattr(spec, "wired", False):
        return spec
    try:
        return rgraph.read_graph(_with_frame(copy.deepcopy(_frame_doc(spec))))
    except rgraph.GraphError:
        return None


def picture_sources(spec) -> list[str]:
    """Every picture-making node section `spec` reaches or declares
    (`frame_names`: its entries and its wires' ends), in area order —
    MEDIA, SCENE, LOOK-BACK, EFFECTS — and section order within one: what
    a page's picture combo may offer (plan 35 U). No geometry, no window,
    no `ground` (the combo's "nothing" says that)."""
    names = [n for n in frame_names(spec) if kind_of(n) in PICTURE_AREA
             and _makes(kind_of(n)) == IMAGE]
    return sorted(names, key=lambda n: PICTURE_AREAS.index(PICTURE_AREA[kind_of(n)]))


def _window(port: str) -> int | None:
    """The window `port` is the picture port of (`output.2.image` → 2), or
    None (All outputs', the capture)."""
    head, _, rest = port.partition(".")
    n, _, p = rest.partition(".")
    return int(n) if head == "output" and n.isdigit() and p == "image" else None


def picture_choices(spec, port: str, reg=None) -> list[str]:
    """A picture combo's items for `port`: a window's "as All outputs",
    "nothing" and `picture_sources`; All outputs' and the capture's
    "nothing" and the sources. R17: on an output's port (a window's, All
    outputs') with `reg` to ask, every channel with a source in its bin
    (`channel_bins`) too, though nothing wires it yet — after the graph's
    own, by label — so "this channel on this window" is one pick."""
    head = [AS_ALL, NOTHING] if _window(port) is not None else [NOTHING]
    got = picture_sources(spec)
    if reg is not None and (_window(port) is not None or port == f"{rgraph.ALL_OUTPUTS}.image"):
        filled = [f"channel.{c}" for c in channel_bins(reg)]
        got += sorted((c for c in filled if c not in got), key=label_of)
    return [*head, *got]


def _into(spec, dst: str) -> str | None:
    return next((w.src for w in (spec.wires if spec is not None else ()) if w.dst == dst), None)


def picture_now(spec, port: str, rig=None) -> str:
    """The combo's pick for `port` as section `spec` wires it: the source's
    name; `ground`, or no wire (All outputs', the capture), "nothing"; a
    window with no wire of its own, "as All outputs" while the rig's bus
    cable into its picture stands (`rig`, plan 36 T1; None: every one),
    else "nothing"; one putting the hands through All outputs' picture
    (`is_through`), "as All outputs" (a through over nothing — the scene
    off — "nothing")."""
    n = _window(port)
    if n is not None and is_through(spec, n, rig):
        under = rgraph.through_of(spec.wiring(), n, rig)[1]
        return AS_ALL if under is not None else NOTHING
    src = _into(spec, port)
    if src is None:
        standing = n is not None and (rig is None or rig.has(rgraph.bus_wire(n, "image")))
        return AS_ALL if standing else NOTHING
    return NOTHING if src == rgraph.GROUND else src


def picture_label(spec, name: str, slots=()) -> str:
    """A combo item's words: "as All outputs" and "nothing" as they are,
    a node by its title (`label_of`; a copy with what it copies)."""
    if name in (AS_ALL, NOTHING):
        return name
    of = next((c.of for c in (getattr(spec, "copies", None) or ()) if c.name == name), "")
    return label_of(name, slots, of=of)


def is_through(spec, n: int, rig=None) -> bool:
    """Whether window `n` puts the hands through the effects: its picture
    a chain over a composite laying a hands layer (`graph.through_of`;
    `rig`, the bus cables standing)."""
    return spec is not None and rgraph.through_of(spec.wiring(), n, rig) is not None


def _drop_through(doc: dict, n: int) -> bool:
    """Window `n`'s "hands through the effects" taken out of section `doc`
    (the inverse of `graphmigrate.through_wires`, plan 36 T1): the wire into its picture, the chain of copies back to the
    composite and the composite — each that nothing else reads, with its
    entry and its wires — and the `ground` the through put on its hands
    port, so the layer is laid over again. A through over nothing (the
    scene off) leaves `ground` on the picture port. False: not through."""
    wires = doc.get("wires", [])
    into = {x["to"]: x["from"] for x in wires}
    port = f"output.{n}."
    chain: list[str] = []
    src = into.get(port + "image")
    while kind_of(src) == "copy" and src not in chain:
        chain.append(src)
        src = into.get(f"{src}.image")
    if kind_of(src) != "composite" or kind_of(into.get(f"{src}.over")) != "layer":
        return False
    chain.append(src)
    under = into.get(f"{src}.under")
    left = [x for x in wires if x["to"] != port + "image"
            and not (x["to"] == port + "hands" and x["from"] == rgraph.GROUND)]
    gone: set[str] = set()
    for name in chain:                     # the window's end first, back to the composite
        if any(x["from"] == name for x in left):
            break                          # (read by something else: kept, and what feeds it)
        gone.add(name)
        left = [x for x in left if x["to"].rpartition(".")[0] != name]
    dropped = [x for x in wires if x not in left]
    doc["wires"] = left
    doc["nodes"] = [e for e in doc.get("nodes", []) if _node_name(e) not in gone]
    if under is None:
        doc["wires"].append({"from": rgraph.GROUND, "to": port + "image"})
    _keep_declared(doc, [x["from"] for x in dropped if x["from"] not in gone])
    return True


def set_picture(edit: Edit, port: str, choice: str) -> str | None:
    """A page's picture combo (plan 35 U): `choice` into `port` — a
    window's (`output.N.image`), All outputs' or the look-back's capture —
    the one wire into that port and nothing else (plan 36 T1). A source is
    `render_wire(…, port)`; "nothing" is `ground` into a window's port, no
    wire into the others'; "as All outputs" is the rig's bus cable into the
    window's picture: its own wire goes and the cable is joined if the show
    had cut it. A through window's chain is not taken out with it (that is
    the through tick's): what it leaves reaches nothing, drawn faint. One
    undo step; a pick that is so already lands nothing ("already so")."""
    spec = _spec(edit)
    rig = _rig(edit)
    if picture_now(spec, port, rig) == choice:
        edit.said = "already so"
        return None
    n = _window(port)
    doc = _doc(edit)
    if choice == NOTHING and n is not None:
        choice = rgraph.GROUND
    if choice not in (AS_ALL, NOTHING):
        return render_wire(edit, choice, port, doc=doc)
    wires = doc.get("wires", [])
    left = [x for x in wires if x["to"] != port]
    gone = [x for x in wires if x not in left]
    doc["wires"] = left
    _keep_declared(doc, [x["from"] for x in gone])
    if choice == AS_ALL and n is not None:
        return _land(edit, doc, f"unwire {port}", f"{port}: {AS_ALL}",
                     rig=rig.joining(rgraph.bus_wire(n, "image")))
    return _land(edit, doc, f"unwire {port}", f"unwired {port}")


def through_refusal(spec, n: int, slots=(), rig=None) -> str | None:
    """Why window `n` cannot put the hands through the effects (the
    checkbox drawn disabled, its hover these words), or None: All outputs
    lays no hands layer over its picture (R11: no hands to put through),
    the window shows a picture of its own by a wire, (plan 36 T1, `rig`)
    its picture cable from All outputs is cut so it shows none, or the
    preset wires its hands port itself — the toggle would drop that wire,
    and it never drops a wire it did not write (through off puts back
    exactly what through on took)."""
    if kind_of(_into(spec, f"{rgraph.ALL_OUTPUTS}.hands")) != "layer":
        return THROUGH_NO_LAYER
    label = label_of(f"output.{n}", slots)
    own = _into(spec, f"output.{n}.image")
    if own is not None and own != rgraph.GROUND and not is_through(spec, n, rig):
        return THROUGH_OWN_PICTURE.format(label=label, src=picture_label(spec, own))
    if own is None and rig is not None and not rig.has(rgraph.bus_wire(n, "image")):
        return THROUGH_NO_PICTURE.format(label=label)
    hands = _into(spec, f"output.{n}.hands")
    if hands is not None:
        return THROUGH_OWN_HANDS.format(label=label, src=hands, n=n)
    return None


def set_through(edit: Edit, n: int, on: bool) -> str | None:
    """OUTPUT's "hands through the effects" on window `n` (plan 35 O, T4's
    carried toggle), as wiring — the wires it names and nothing else (plan
    36 T1: no `_Wiring._put` rule): on, `graphmigrate.through_wires` — a
    composite laying All outputs' hands layer on its picture's head and a
    copy of each effect of its run, into `output.n.image` (with the
    window's picture `ground`, the hands alone through), and `ground` into
    `output.n.hands` (the layer goes through, not over again); off, those
    wires and the composite and copies only they use (`_drop_through`).
    The guide port is never touched. One undo step each. Refused in words:
    All outputs laying no hands layer (R11), a window with a picture of
    its own."""
    spec = _spec(edit)
    if spec is None:
        return "no preset is loaded"
    label = label_of(f"output.{n}", getattr(edit, "slots", ()))
    rig = _rig(edit)
    if is_through(spec, n, rig) == on:
        edit.said = "already so"
        return None
    doc = _doc(edit)
    if not on:
        _drop_through(doc, n)
        return _land(edit, doc, f"hands over on output {n}",
                     f"{label}: the hands over the effects")
    why = through_refusal(spec, n, getattr(edit, "slots", ()), rig)
    if why is not None:
        return why
    got = graphmigrate.through_wires(spec, n, rig)
    port = f"output.{n}."
    doc["nodes"] += [x for x in got if "kind" in x]
    doc["wires"] = [x for x in doc.get("wires", [])
                    if x["to"] not in (port + "image", port + "hands")]
    doc["wires"] += [x for x in got if "kind" not in x]
    return _land(edit, doc, f"hands through on output {n}",
                 f"{label}: the hands through the effects")
