"""Patches — a group of nodes and its boundary, as data (plan 40 P1).

A **patch** is a preset fragment with a boundary: the nodes of a region of
the GRAPH page, their values, the wires among them, the routes, desk rows,
modifiers, voices and macro subscribers among them — and every cable that
crosses the region's edge. Its file is ``<library>/patches/<slug>.json``,
``hyperspace.patch/1``, in the preset's own keys plus one, ``ports``::

    {"schema": "hyperspace.patch/1", "name": "acid wash", "note": "…",
     "nodes":  [{"kind": "effect", "file": "acid"}, {"kind": "delay"}, …],
     "wires":  [{"from": "acid", "to": "wobble.image"}, …],
     "values": {"fx.acid.speed": 0.4, …},
     "modifiers": [{"id": "mod.1", "kind": "smooth", "in": ["hand:right.y"], …}],
     "routes": [{"source": "mod:1", "target": "fx.wobble.amount", "op": "push", …}],
     "desk":   [{"source": "cc:0:48", "target": "fx.acid.speed", "op": "abs", …}],
     "macros": {}, "lfos": [], "envs": [],
     "ports":  [{"id": "in", "type": "image", "to": "acid.image", "was": "scene"},
                {"id": "out", "type": "image", "from": "delay", "was": "output.all.image"}],
     "layout": {"render:acid": [0, 0], …}}

Its ids are its own, the lowest as if it were alone (`acid`, `mod.1`,
`lfo.1`; an envelope from 6, the lane envelopes 1–5 being every preset's;
a macro keeps its number, there are eight); its layout is relative to its
own origin. ``ports`` holds only the picture / geometry / mask cables that
cross the edge (an inlet's ``was`` the source it came from, an outlet's
the port it went into). **The rest of the boundary is classified at read,
not stored twice** (`read`):

- a **rig row** — a route or desk row whose source is not the patch's own
  (anything but a ``mod:`` / ``lfo:`` / ``env:`` lane of an id it holds,
  or a macro it holds): a knob, a hand axis, an audio band, a pad stick,
  an OSC fader — kept verbatim, the absolute address it is;
- a **host port** — every ``ports`` entry, and, derived from the rows: a
  route from a patch lane onto a param the patch does not hold, a route
  from a lane of the host's (a ``lfo:0`` of an LFO the patch does not
  hold) onto one it does, a member macro's base subscriber onto a host
  param, a modifier input read from a host lane.

D5 (the owner's): a patch **drives** a host param through a port, it never
**sets** one — ``values`` holds only its members' params.

Four functions: `check` (the refusals in words), `read` (the fragment and
its boundary), `lift` (cut a patch out of a loaded preset's parts: the
pure half of *save as patch*) and `spawn` (what landing it in another
preset would add: the pure half of *spawn*, P3 lands it through today's
doors as one undo step). A leaf like `graphmigrate.py`: pure data in, pure
data out — it imports `graph`'s names and helpers, `routing`'s `Binding`
and scheme split and the modifiers' id rule, and nothing of the app.
`library` imports it (for `check`), never the reverse.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from . import envelope as envmod
from . import graph as G
from . import lfo as lfomod
from . import modbank
from . import modifiers as modmod
from .routing import Binding, base_scheme, is_continuous, is_macro

KIND = "hyperspace.patch"
VERSION = 1
SCHEMA = f"{KIND}/{VERSION}"
# the file's keys, in the order a lift writes them
KEYS = ("schema", "name", "note", "nodes", "wires", "values", "modifiers", "routes", "desk",
        "macros", "lfos", "envs", "ports", "layout")

# what a patch may hold of the render graph (P1): what can be made twice —
# the kinds `graph.wire_node_kind(…, wired=True)` names; `hands`, `layer`
# and `guide` only for an extra hands (`hands.2` …), hands 1 being the frame's
MAY_HOLD = ("effect", "composite", "switch", "delay", "resize", "copy", "matte", "cut",
            "segment", "hands", "layer", "guide")
HANDS_KINDS = ("hands", "layer", "guide")
# the rig's render nodes the GRAPH page never deletes — `graphview.spec_name`'s
# `NOT_REMOVABLE` refusal names the camera and the clouds (the windows are
# refused by kind, `output`). Copied, not imported (graphview is the app's);
# tests/test_patches.py holds the two lists equal
RIG_NODES = ("camera", "cloud")
# the modulation banks a patch carries voices of, and the canvas ids
LFO, ENV, MOD, MACRO = "lfo", "env", modmod.SCHEME, "macro"
VOICES = (LFO, ENV)
# the sequencer's lane envelopes (`envelope.LANE_ENVS`): every preset's, so a
# patch never carries one by identity — its envelopes are 6 and up
LANE_ENVS = envmod.LANE_ENVS
FIRST_ENV = max(LANE_ENVS) + 1
MACROS = 8                     # macro.1 … macro.8, the rig's eight knobs
# the rig-side sources one control drives one param from (the Learn rule:
# "one axis, one param", plan 18 fork 7) — a patch row on one of these that
# the host already sends somewhere else is a conflict (P3's sheet). A desk
# control is judged by `Binding.overlaps` instead; every other scheme (an
# audio band, an LFO, an OSC fader) may drive any number of params
ONE_OWNER = ("hand", "axis")

# the refusals' words (P1: name the thing and why)
FRAME_WORDS = "{name} is the frame's; left out"
WINDOW_WORDS = "{name} is the rig's window; left out — a patch's picture leaves by a port"
RIG_WORDS = "{name} is the rig's; left out"
CHANNEL_WORDS = ("{name} is a media channel, this Mac's files; left out — a patch reads one "
                 "through a port")
NOT_HELD_WORDS = ("{name}: a patch holds effects, composites, switches, delays, resizes, "
                  "copies, extra hands, mattes, cuts and segments; left out")
SEQ_WORDS = "the sequencer is the rig's; left out"
LANE_ENV_WORDS = ("{name} is a sequencer lane's envelope; left out (a patch's envelope "
                  "spawns as {first} or more)")
NO_NODE_WORDS = "{name}: no such node; left out"
COPY_WORDS = "{name} draws {of} again: take {of} with it; left out"
HOST_MACRO_WORDS = ("{mid} is not in the patch: its subscriber on {pid} stays the preset's "
                    "(take {mid} with it)")
NO_MACRO_NOTE = "{mid}: no free macro — its subscribers not spawned"
NO_VOICE_NOTE = "{vid}: {why} — not spawned, nor its routes"
NO_INPUT_NOTE = "{mid}: its input {k} read {vid}, which did not spawn — left empty"
CROSSES_WORDS = "wire {wire} crosses the edge: a port says it"
# a node entry of a kind that is no node a section declares but names a
# thing a patch may not hold (`check`): said as that thing
_KIND_WORDS = {"output": WINDOW_WORDS, "camera": RIG_WORDS, "cloud": RIG_WORDS,
               "channel": CHANNEL_WORDS, "media": CHANNEL_WORDS}


def slug(name: str) -> str:
    """A patch's file stem from its name — `library.slug`'s rule, restated
    (library imports this module, not the reverse; the tests hold the two
    equal)."""
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return s or "untitled"


# ---------------------------------------------------------------- names

def _kind(name: str) -> str | None:
    """A render node name's kind as the GRAPH page reads it
    (`graphview.kind_of`, restated): a wired frame's kinds, All outputs as
    an output, the rig's camera and clouds."""
    if not isinstance(name, str):
        return None
    if name == G.ALL_OUTPUTS:
        return "output"
    if name == "camera":
        return "camera"
    if name == G.CLOUD_KIND or name.startswith(f"{G.CLOUD_KIND}."):
        return "cloud"
    return G.wire_node_kind(name, wired=True)


def _node_of(src: str) -> str:
    """A wire's source → the node it is an output of (a pin is its node:
    `segment.2.fg` → `segment.2`, `scene.depth` → `scene`)."""
    return G.pin_node(src) or src


def _family(name: str) -> tuple[str, int, str]:
    """A render node name → (its base, its instance, a suffix): `acid.2` →
    ("acid", 2, ""), `hands.3.layer` → ("hands", 3, ".layer"). The base and
    instance are what a rename moves — a hands node, its layer and its
    guide move together."""
    kind = _kind(name)
    if kind in ("layer", "guide"):
        base, n = G.split_instance(G.hands_of(name))
        return base, n, f".{kind}"
    head, _, tail = name.partition(".")
    if tail.isdecimal():
        return head, int(tail), ""
    return name, 1, ""


def _join(base: str, n: int, suffix: str = "") -> str:
    return (base if n == 1 else f"{base}.{n}") + suffix


def _instance_of(name: str) -> int:
    return _family(name)[1]


def held_words(name: str) -> str | None:
    """Why render node `name` may not be in a patch, in words — None when
    it may (P1's list: what can be made twice)."""
    kind = _kind(name)
    if kind in RIG_NODES:
        return RIG_WORDS.format(name=name)
    if kind == "output":
        return WINDOW_WORDS.format(name=name)
    if kind == "channel":
        return CHANNEL_WORDS.format(name=name)
    if kind in HANDS_KINDS and _instance_of(name) == 1:
        return FRAME_WORDS.format(name=name)
    if kind in G.FRAME_KINDS:
        return FRAME_WORDS.format(name=name)
    if kind not in MAY_HOLD:
        return NOT_HELD_WORDS.format(name=name) if kind is not None else (
            NO_NODE_WORDS.format(name=name))
    return None


def entry_name(e: Mapping) -> str | None:
    """A graph section's node entry → the node's name (`{"kind": "effect",
    "file": "acid", "instance": 2}` → `acid.2`), or None for one that names
    nothing this build reads."""
    kind, n = e.get("kind"), e.get("instance", 1)
    if not isinstance(kind, str) or not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return None
    if kind == "effect":
        f = e.get("file")
        return G.instance_name(f, n) if isinstance(f, str) and f else None
    if kind == "hands":
        return G.wired_hands_name(n)
    if kind == "layer":
        return G.wired_layer_name(n)
    if kind == "guide":
        return G.wired_guide_name(n)
    return _join(kind, n)


def _entry_for(name: str) -> dict:
    """The minimal entry declaring render node `name` (an effect named only
    by its wires, a layer named only by a wire)."""
    kind = _kind(name)
    base, n, _ = _family(name)
    if kind == "effect":
        return {"kind": "effect", "file": base, **({"instance": n} if n != 1 else {})}
    return {"kind": kind, **({"instance": n} if n != 1 else {})}


def spec_names(spec: G.GraphSpec | None) -> frozenset[str]:
    """Every render node a loaded section has: its entries' and its wires'
    ends (a pin as its node), hands 1 in a wired frame."""
    if spec is None:
        return frozenset()
    out = {name for e in spec.to_json().get("nodes", []) if (name := entry_name(e))}
    for w in spec.all_wires():
        out.add(_node_of(w.src))
        out.add(w.node)
    out.discard(G.GROUND)
    return frozenset(out)


def _voice(cid: str) -> tuple[str, int] | None:
    """`lfo.3` → ("lfo", 3), `env.7` → ("env", 7), `mod.2` → ("mod", 2),
    `macro.4` → ("macro", 4); None for any other canvas id."""
    head, dot, n = cid.partition(".")
    if dot and n.isdecimal() and str(int(n)) == n and int(n) >= 1:
        if head in (LFO, ENV, MOD):
            return head, int(n)
        if head == MACRO and int(n) <= MACROS:
            return head, int(n)
    return None


def _lane(addr: str) -> tuple[str, int] | None:
    """A source address that is a modulation lane → (its bank or ``mod``,
    the voice id it is): ``lfo:0`` → ("lfo", 1), ``env:6`` → ("env", 7),
    ``mod:3`` → ("mod", 3). None for any other source (a rig's)."""
    if not isinstance(addr, str):
        return None
    head, _, tail = addr.partition(":")
    if head not in (LFO, ENV, MOD) or not tail.isdecimal():
        return None
    i = int(tail)
    if head == MOD:
        return (MOD, i) if i >= 1 else None
    return head, i + 1


def _lane_of(scheme: str, n: int) -> str:
    """The lane address of voice `n` of `scheme` (``lfo`` 1 → ``lfo:0``,
    ``mod`` 3 → ``mod:3``)."""
    return f"{scheme}:{n if scheme == MOD else n - 1}"


# ---------------------------------------------------------------- the members

@dataclass(frozen=True)
class _Members:
    """A patch's members by kind: its render node names, and its modifier,
    LFO, envelope and macro numbers."""

    render: tuple[str, ...] = ()
    mods: tuple[int, ...] = ()
    lfos: tuple[int, ...] = ()
    envs: tuple[int, ...] = ()
    macros: tuple[int, ...] = ()

    def ids(self, scheme: str) -> tuple[int, ...]:
        return {MOD: self.mods, LFO: self.lfos, ENV: self.envs, MACRO: self.macros}[scheme]

    def prefixes(self) -> dict[str, str]:
        """param prefix → the member that owns it (`fx.acid.2` → `acid.2`,
        `ghost.2` → `hands.2`, `lfo.3` → `lfo.3`)."""
        out: dict[str, str] = {}
        for name in self.render:
            if _kind(name) == "copy":
                continue                 # a copy's knobs are its original's
            pre = G.param_prefix(name)
            out.setdefault(pre, name)
        for scheme in (MOD, LFO, ENV):
            for n in self.ids(scheme):
                out[f"{scheme}.{n}"] = f"{scheme}.{n}"
        return out

    def owns(self, pid: Any) -> bool:
        return _owner(pid, self.prefixes(), self.macros) is not None

    def own_lane(self, addr: Any) -> bool:
        hit = _lane(addr)
        return hit is not None and hit[1] in self.ids(hit[0])

    def canvas(self) -> list[str]:
        """The members as GRAPH canvas ids, in drawing order."""
        return ([f"render:{n}" for n in self.render]
                + [f"{MOD}.{n}" for n in self.mods] + [f"{LFO}.{n}" for n in self.lfos]
                + [f"{ENV}.{n}" for n in self.envs] + [f"{MACRO}.{n}" for n in self.macros])


def _owner(pid: Any, prefixes: Mapping[str, str], macros: Iterable[int]) -> str | None:
    """The member whose param `pid` is, or None. A prefix owns ``<prefix>.<key>``
    unless the key's first part is a number — ``fx.acid.2.mix`` is acid.2's,
    never acid's."""
    if not isinstance(pid, str):
        return None
    if is_macro(pid) and int(pid.partition(".")[2]) in set(macros):
        return pid
    best = None
    for pre, who in prefixes.items():
        if pid.startswith(pre + ".") and (best is None or len(pre) > len(best[0])):
            rest = pid[len(pre) + 1:]
            if rest and not rest.split(".", 1)[0].isdecimal():
                best = (pre, who)
    return best[1] if best is not None else None


def _members_of(doc: Mapping) -> _Members:
    render = []
    for e in doc.get("nodes") or ():
        if isinstance(e, Mapping) and (name := entry_name(e)) is not None:
            render.append(name)
    mods = [modmod.number(m.get("id")) for m in doc.get("modifiers") or ()
            if isinstance(m, Mapping)]
    macros = [int(k.partition(".")[2]) for k in (doc.get("macros") or {})
              if isinstance(k, str) and is_macro(k)]
    return _Members(tuple(render), tuple(n for n in mods if n),
                    tuple(_ints(doc.get("lfos"))), tuple(_ints(doc.get("envs"))),
                    tuple(sorted(n for n in macros if 1 <= n <= MACROS)))


def _ints(value: Any) -> list[int]:
    return [v for v in (value or ()) if isinstance(v, int) and not isinstance(v, bool)]


# ---------------------------------------------------------------- renaming

@dataclass
class _Renamer:
    """One rename of a patch's ids: render families ``(base, n) → n'`` and
    each bank's ``n → n'`` (a macro's ``N → N'``). Anything not a member is
    left as it is."""

    members: _Members
    render: dict[tuple[str, int], int] = field(default_factory=dict)
    voices: dict[str, dict[int, int]] = field(default_factory=dict)
    gone: dict[str, set[int]] = field(default_factory=dict)    # members that did not spawn

    def __post_init__(self) -> None:
        self._prefixes = self.members.prefixes()
        self._families = {_family(name)[:2] for name in self.members.render}

    # names
    def name(self, name: str) -> str:
        """A render name renamed when it is a member's (a member hands' layer
        and guide with it); any other as it is."""
        base, n, suffix = _family(name)
        if (base, n) not in self._families:
            return name
        return _join(base, self.render.get((base, n), n), suffix)

    def src(self, src: str) -> str:
        node = _node_of(src)
        if node == src:
            return self.name(src)
        return self.name(node) + src[len(node):]

    def dst(self, dst: str) -> str:
        node, _, port = dst.rpartition(".")
        return f"{self.name(node)}.{port}"

    def voice(self, scheme: str, n: int) -> int:
        return self.voices.get(scheme, {}).get(n, n)

    def lane(self, addr: Any) -> Any:
        """A member's lane renamed; a lane of a member that did not spawn
        (`gone`: a full bank) resolves to nothing — None, never its old
        number, which would read the host's voice of that id."""
        hit = _lane(addr)
        if hit is None or hit[1] not in self.members.ids(hit[0]):
            return addr
        if hit[1] in self.gone.get(hit[0], ()):
            return None
        return _lane_of(hit[0], self.voice(*hit))

    def param(self, pid: Any) -> Any:
        if not isinstance(pid, str):
            return pid
        if is_macro(pid):
            n = int(pid.partition(".")[2])
            return f"{MACRO}.{self.voice(MACRO, n)}" if n in self.members.macros else pid
        who = _owner(pid, self._prefixes, ())
        if who is None:
            return pid
        pre = next(p for p, w in self._prefixes.items() if w == who and pid.startswith(p + "."))
        vo = _voice(who)
        new = (G.param_prefix(self.name(who)) if vo is None
               else f"{vo[0]}.{self.voice(*vo)}")
        return new + pid[len(pre):]

    def canvas(self, cid: str) -> str:
        if cid.startswith("render:"):
            return "render:" + self.name(cid[len("render:"):])
        vo = _voice(cid)
        return cid if vo is None else f"{vo[0]}.{self.voice(*vo)}"

    # documents
    def entry(self, e: Mapping) -> dict:
        out = dict(e)
        name = entry_name(e)
        if name is not None:
            n = _family(self.name(name))[1]
            out.pop("instance", None)
            if n != 1:
                out["instance"] = n
        if out.get("kind") == "copy" and isinstance(out.get("of"), str):
            out["of"] = self.name(out["of"])
        return out

    def wire(self, w: Mapping) -> dict:
        return {"from": self.src(w["from"]), "to": self.dst(w["to"])}

    def row(self, r: Mapping) -> dict:
        out = dict(r)
        out["source"] = self.lane(out.get("source"))
        out["target"] = self.param(out.get("target"))
        if isinstance(out.get("when"), str):
            out["when"] = self.lane(out["when"])
        return out

    def modifier(self, m: Mapping) -> dict:
        out = dict(m)
        n = modmod.number(out.get("id"))
        if n is not None:
            out["id"] = f"{modmod.PREFIX}{self.voice(MOD, n)}"
        ins = out.get("in")
        if isinstance(ins, list):
            out["in"] = [self.lane(a) if a else a for a in ins]
        elif isinstance(ins, str):
            out["in"] = self.lane(ins)
        return out

    def macro(self, m: Mapping) -> dict:
        out = dict(m)
        subs = []
        for s in m.get("subs") or ():
            s = dict(s)
            if isinstance(s.get("base"), str):
                s["base"] = self.param(s["base"])
            dep = s.get("depth")
            if isinstance(dep, Mapping):
                s["depth"] = {"source": self.lane(dep.get("source")),
                              "target": self.param(dep.get("target"))}
            subs.append(s)
        out["subs"] = subs
        return out

    def port(self, p: Mapping) -> dict:
        out = dict(p)
        if isinstance(out.get("to"), str) and "." in out["to"]:
            out["to"] = self.dst(out["to"])
        if isinstance(out.get("from"), str):
            out["from"] = self.src(out["from"])
        return out


# ---------------------------------------------------------------- read

@dataclass(frozen=True)
class Patch:
    """A patch file, read (`read`): the fragment in the preset's own keys,
    the file's `ports`, and the two classified boundary lists — `rig_rows`
    (every route or desk row whose source is not the patch's own) and
    `host_ports` (every `ports` entry, then the value crossings derived
    from the rows: each ``{"id": "value.<k>", "type": "value",
    "to" | "from", "was", "row"?}``)."""

    name: str
    note: str
    nodes: tuple[dict, ...]
    wires: tuple[dict, ...]
    values: dict[str, Any]
    modifiers: tuple[dict, ...]
    routes: tuple[dict, ...]
    desk: tuple[dict, ...]
    macros: dict[str, dict]
    lfos: tuple[int, ...]
    envs: tuple[int, ...]
    layout: dict[str, list[float]]
    ports: tuple[dict, ...]
    rig_rows: tuple[dict, ...]
    host_ports: tuple[dict, ...]

    @property
    def members(self) -> _Members:
        return _members_of({"nodes": self.nodes, "modifiers": self.modifiers,
                            "lfos": self.lfos, "envs": self.envs, "macros": self.macros})


def _wire_key(w: Mapping) -> tuple[str, str]:
    return (str(w.get("from")), str(w.get("to")))


def _entry(d: Mapping) -> dict:
    """A modifier's entry in full (every param, as a preset writes it), so a
    file that leaves a default out reads as one that says it; one this build
    cannot read as it is (`check` refuses it)."""
    try:
        return modmod.Modifier.from_json(dict(d)).to_json()
    except (ValueError, TypeError):
        return dict(d)


def read(doc: Mapping) -> Patch:
    """A patch document → its `Patch`: the fragment as the file says it
    (nodes by name, wires and ports in a fixed order, so two equal patches
    read equal), and its boundary classified. Tolerant: a shape `check`
    would refuse reads as what it can; the library refuses before this."""
    nodes = tuple(sorted((dict(e) for e in doc.get("nodes") or () if isinstance(e, Mapping)),
                         key=lambda e: (entry_name(e) or "", str(e))))
    m = _members_of({**doc, "nodes": nodes})
    wires = tuple(sorted((dict(w) for w in doc.get("wires") or () if isinstance(w, Mapping)),
                         key=_wire_key))
    routes = tuple(dict(r) for r in doc.get("routes") or () if isinstance(r, Mapping))
    desk = tuple(dict(r) for r in doc.get("desk") or () if isinstance(r, Mapping))
    mods = tuple(sorted((_entry(x) for x in doc.get("modifiers") or () if isinstance(x, Mapping)),
                        key=lambda x: modmod.number(x.get("id")) or 0))
    macros = {k: dict(v) for k, v in sorted((doc.get("macros") or {}).items(),
                                           key=lambda kv: _macro_n(kv[0]))
              if isinstance(v, Mapping)}
    ports = tuple(sorted((dict(p) for p in doc.get("ports") or () if isinstance(p, Mapping)),
                         key=lambda p: str(p.get("id"))))
    rig: list[dict] = []
    host: list[dict] = list(ports)
    k = 0

    def value_port(**kw) -> None:
        nonlocal k
        k += 1
        host.append({"id": f"value.{k}", "type": G.VALUE, **kw})

    for r in (*routes, *desk):
        src, tgt = r.get("source"), r.get("target")
        where = side(m, src, tgt)
        if where == RIG:
            rig.append(r)                         # a knob, a hand, a band: verbatim
        elif where == INTO:
            value_port(to=tgt, was=src, row=r)    # a host lane onto a member
        elif where == OUT:
            value_port(**{"from": src}, was=tgt, row=r)   # a member lane onto a host param
    for mid, mac in macros.items():
        for s in mac.get("subs") or ():
            base = s.get("base") if isinstance(s, Mapping) else None
            if isinstance(base, str) and sub_side(m, mid, base) == OUT:
                value_port(**{"from": mid}, was=base)
    for mod in mods:
        ins = mod.get("in")
        ins = [ins] if isinstance(ins, str) else list(ins or ())
        for i, a in enumerate(ins):
            if a and input_side(m, mod.get("id"), a) == INTO:
                value_port(to=f"{mod.get('id')}.in{i + 1}", was=a)
    layout = {}
    for cid, xy in (doc.get("layout") or {}).items():
        try:
            x, y = (float(v) for v in xy)
        except (TypeError, ValueError):
            continue
        layout[str(cid)] = [round(x), round(y)]
    return Patch(name=str(doc.get("name") or ""), note=str(doc.get("note") or ""),
                 nodes=nodes, wires=wires, values=dict(doc.get("values") or {}),
                 modifiers=mods, routes=routes, desk=desk, macros=macros,
                 lfos=tuple(sorted(m.lfos)), envs=tuple(sorted(m.envs)), layout=layout,
                 ports=ports, rig_rows=tuple(rig), host_ports=tuple(host))


def _macro_n(mid: Any) -> int:
    return int(mid.partition(".")[2]) if isinstance(mid, str) and is_macro(mid) else 0


# ---------------------------------------------------------------- check

def check(doc: Any) -> list[str]:
    """The reasons `doc` is no patch this build can spawn, in words — []
    when it is one. The schema and the shape of every key; a node a patch
    may not hold (a frame singleton, an output, a cloud, the camera, a
    media channel, a look-back); a port of an unknown type or onto no
    member; a wire to a node the patch lacks that no port covers; a value
    of a param no member has (D5); a lane envelope 1–5."""
    if not isinstance(doc, Mapping):
        return [f"a patch is a JSON object, not {type(doc).__name__}"]
    out: list[str] = []
    if doc.get("schema") != SCHEMA:
        out.append(f"schema {doc.get('schema')!r} is not {SCHEMA}")
    extra = sorted(set(doc) - set(KEYS))
    if extra:
        out.append(f"no key {', '.join(map(repr, extra))} in a patch")
    if not isinstance(doc.get("name", ""), str) or not isinstance(doc.get("note", ""), str):
        out.append("name and note are text")
    for key, typ in (("nodes", list), ("wires", list), ("values", dict), ("modifiers", list),
                     ("routes", list), ("desk", list), ("macros", dict), ("lfos", list),
                     ("envs", list), ("ports", list), ("layout", dict)):
        if key in doc and not isinstance(doc[key], typ):
            out.append(f"{key} is not a {'list' if typ is list else 'map'}")
    if out:
        return out
    m = _members_of(doc)
    for e in doc.get("nodes") or ():
        name = entry_name(e) if isinstance(e, Mapping) else None
        said = _KIND_WORDS.get(e.get("kind")) if isinstance(e, Mapping) else None
        if said is not None:
            out.append(said.format(name=e["kind"]))
            continue
        if name is None:
            out.append(f"a node this build cannot read: {e!r}"[:120])
            continue
        why = held_words(name)
        if why is not None:
            out.append(why)
        elif e.get("kind") == "copy" and e.get("of") not in m.render:
            out.append(COPY_WORDS.format(name=name, of=e.get("of")))
    if len(set(m.render)) != len(m.render):
        out.append("a node named twice")
    held = set(m.render)
    ports = [p for p in doc.get("ports") or ()]
    seen: set[str] = set()
    for p in ports:
        if not isinstance(p, Mapping) or not isinstance(p.get("id"), str) or not p["id"]:
            out.append(f"a port with no id: {p!r}"[:120])
            continue
        pid = p["id"]
        if pid in seen:
            out.append(f"port {pid}: named twice")
        seen.add(pid)
        if p.get("type") not in G.PORT_TYPES:
            out.append(f"port {pid}: type {p.get('type')!r} is not one of "
                       f"{', '.join(G.PORT_TYPES)}")
        if ("to" in p) == ("from" in p):
            out.append(f"port {pid}: names one of to (an inlet) or from (an outlet)")
            continue
        end = p.get("to") if "to" in p else p.get("from")
        node = (end.rpartition(".")[0] if "to" in p else _node_of(end)) if isinstance(
            end, str) else None
        if node not in held:
            out.append(f"port {pid}: {end!r} is no node of the patch")
        if not isinstance(p.get("was"), str):
            out.append(f"port {pid}: was names what it was attached to")
    for w in doc.get("wires") or ():
        if not isinstance(w, Mapping) or not isinstance(w.get("from"), str) \
                or not isinstance(w.get("to"), str) or "." not in w["to"]:
            out.append(f"a wire that is not from a node into '<node>.<port>': {w!r}"[:120])
            continue
        src, dst = w["from"], w["to"]
        # a patch's wires are its own, both ends in it; a cable across the edge
        # is a port, never a wire — a wire would be landed by a spawn, an
        # attachment by its saved name (D2, plan 36: no hidden edge)
        for end in (_node_of(src), dst.rpartition(".")[0]):
            if end in held:
                continue
            # (the rig's own ends said as such; any other end — the scene, a
            # host effect — is simply across the edge)
            why = held_words(end) if _kind(end) in ("output", "channel", *RIG_NODES) else None
            out.append(f"wire {src} → {dst}: {why}" if why is not None
                       else CROSSES_WORDS.format(wire=f"{src} → {dst}"))
            break
    for pid in doc.get("values") or {}:
        if str(pid).startswith(modmod.PREFIX):
            out.append(f"{pid} is a modifier's: set in its entry")
        elif not m.owns(pid):
            out.append(f"{pid} is the host's: a patch drives a host param, never sets it (D5)")
    ids: set[str] = set()
    for d in doc.get("modifiers") or ():
        try:
            mod = modmod.Modifier.from_json(d)
        except (ValueError, TypeError) as e:
            out.append(f"modifier {d.get('id') if isinstance(d, Mapping) else d!r}: {e}")
            continue
        if mod.id in ids:
            out.append(f"modifier {mod.id}: named twice")
        ids.add(mod.id)
    for key in ("routes", "desk"):
        for r in doc.get(key) or ():
            if not isinstance(r, Mapping) or not isinstance(r.get("source"), str) \
                    or not isinstance(r.get("target"), str):
                out.append(f"a {key} row with no source or target: {r!r}"[:120])
                continue
            b = Binding.from_json(r)
            if key == "desk" and not b.is_midi:
                out.append(f"desk row {b.source} → {b.target}: not a desk control")
            elif key == "routes" and not is_continuous(b.scheme):
                out.append(f"route {b.source} → {b.target}: not a performer row")
            if not (m.owns(b.target) or m.own_lane(b.source)):
                out.append(f"{key} row {b.source} → {b.target}: nothing of the patch's")
    for mid, mac in (doc.get("macros") or {}).items():
        if not (isinstance(mid, str) and is_macro(mid) and 1 <= _macro_n(mid) <= MACROS):
            out.append(f"macros: {mid!r} is no macro (macro.1 … macro.{MACROS})")
        elif not isinstance(mac, Mapping) or not isinstance(mac.get("subs", []), list):
            out.append(f"{mid}: a macro is {{label, subs}}")
    for key in ("lfos", "envs"):
        vals = doc.get(key) or []
        if len(_ints(vals)) != len(vals) or any(v < 1 for v in _ints(vals)):
            out.append(f"{key}: a list of voice ids")
        if len(set(_ints(vals))) != len(_ints(vals)):
            out.append(f"{key}: an id named twice")
    for n in _ints(doc.get("envs")):
        if n in LANE_ENVS:
            out.append(LANE_ENV_WORDS.format(name=f"env.{n}", first=FIRST_ENV))
    canvas = set(m.canvas())
    for cid in doc.get("layout") or {}:
        if cid not in canvas:
            out.append(f"layout: {cid} is not in the patch")
    return out


# ---------------------------------------------------------------- the boundary
#
# Plan 40 T2: the one classifier of what crosses a region's edge. `lift`
# cuts a patch with it and `read` classifies a file's rows with it; the
# GRAPH page's group node (`graphview.VGroup`) draws a group's boundary
# with it — so a group folded on the canvas shows exactly the pins and
# rows a patch saved from it would have as ports and rig rows.

# where a cable sits against a region: both ends inside; from the rig (a
# knob, a hand, a band) onto a member; from the host onto a member (a host
# lane, a host macro, a picture into a member's port); from a member out
# to the host
INSIDE, RIG, INTO, OUT = "inside", "rig", "into", "out"
NESTED_WORDS = "{name} is a group: a group holds nodes, not groups; left out"


def select(spec: G.GraphSpec | None, table, node_ids: Iterable[str]
           ) -> tuple[_Members, list[str]]:
    """The members a region of GRAPH canvas ids may hold, and, in words,
    every id it may not (P1's rule — `lift`'s, and the GRAPH page's Group):
    a frame singleton, an output, the camera or a cloud, a media channel,
    the sequencer, a lane envelope, a node the section lacks, a modifier
    the table lacks, a copy without its original, a group (no nesting),
    any other canvas id (a device, the analyzer: the rig's). Pure."""
    refused: list[str] = []
    names = spec_names(spec)
    render: list[str] = []
    voices: dict[str, list[int]] = {MOD: [], LFO: [], ENV: [], MACRO: []}
    mods_held = {m.id for m in getattr(table, "modifiers", ())}
    for nid in dict.fromkeys(node_ids):
        if nid.startswith("render:"):
            name = nid[len("render:"):]
            why = held_words(name)
            if why is None and name not in names:
                why = NO_NODE_WORDS.format(name=name)
            if why is not None:
                refused.append(why)
            else:
                render.append(name)
            continue
        vo = _voice(nid)
        if nid == "seq" or nid.startswith("seq:"):
            refused.append(SEQ_WORDS)
        elif re.fullmatch(r"group\.\d+", nid):
            refused.append(NESTED_WORDS.format(name=nid))
        elif vo is None:
            refused.append(RIG_WORDS.format(name=nid))
        elif vo[0] == ENV and vo[1] in LANE_ENVS:
            refused.append(LANE_ENV_WORDS.format(name=nid, first=FIRST_ENV))
        elif vo[0] == MOD and nid not in mods_held:
            refused.append(NO_NODE_WORDS.format(name=nid))
        else:
            voices[vo[0]].append(vo[1])
    entries = {entry_name(e): e for e in (spec.to_json().get("nodes", []) if spec else [])}
    for name in list(render):
        e = entries.get(name)
        if e is not None and e.get("kind") == "copy" and e.get("of") not in render:
            refused.append(COPY_WORDS.format(name=name, of=e.get("of")))
            render.remove(name)
    return _Members(tuple(render), tuple(sorted(voices[MOD])), tuple(sorted(voices[LFO])),
                    tuple(sorted(voices[ENV])), tuple(sorted(voices[MACRO]))), refused


def crossing(spec: G.GraphSpec | None, render: Iterable[str]
             ) -> list[tuple[G.Wire, str]]:
    """Every wire of `spec` with an end on a node of `render`, and where it
    sits: `INSIDE` (both ends members: one of the patch's own wires),
    `INTO` (into a member's port from outside: an inlet port) or `OUT`
    (from a member into a port outside: an outlet port). A pin is its node
    (`segment.2.fg` is `segment.2`'s)."""
    held = set(render)
    out: list[tuple[G.Wire, str]] = []
    for w in (spec.all_wires() if spec is not None else ()):
        a, b = _node_of(w.src) in held, w.node in held
        if a and b:
            out.append((w, INSIDE))
        elif b:
            out.append((w, INTO))
        elif a:
            out.append((w, OUT))
    return out


def wire_type(w: G.Wire, where: str) -> str:
    """The type a crossing wire carries at the region's edge: an inlet's the
    member port's (`WIRED_TAKES`), an outlet's the member's make."""
    if where == INTO:
        return G.WIRED_TAKES.get(_kind(w.node) or "", {}).get(w.port, G.IMAGE)
    return G.WIRED_MAKES.get(_kind(w.src) or "") or G.IMAGE


def touches(members: _Members, source: Any, target: Any) -> bool:
    """Does a row from `source` onto `target` touch the region — land on a
    member's param, or leave a member's lane?"""
    return members.owns(target) or members.own_lane(source)


def side(members: _Members, source: Any, target: Any) -> str:
    """Where a route or desk row sits against the region (`read`'s rule):
    `RIG` — its source is no lane, the absolute address it is (a knob, a
    hand axis, an audio band); `INTO` — a lane the region does not hold
    (a host LFO) onto it; `OUT` — a member's lane onto a param the region
    does not hold; else `INSIDE`. Ask `touches` first: a row that touches
    nothing of the region is none of these."""
    own_src = members.own_lane(source)
    if not own_src and _lane(source) is None:
        return RIG
    if not own_src:
        return INTO
    if not members.owns(target):
        return OUT
    return INSIDE


def sub_side(members: _Members, mid: Any, pid: Any) -> str | None:
    """Where macro `mid`'s subscriber on param `pid` (a base's param, or
    the target of the route a depth scales) sits: `INSIDE`, `OUT` (a member
    macro onto a host param: a host port), `INTO` (a host macro onto a
    member: the preset's, `HOST_MACRO_WORDS` at a lift); None when it
    touches nothing of the region."""
    own_m, own_p = _macro_n(mid) in members.macros, members.owns(pid)
    if own_m:
        return INSIDE if own_p else OUT
    return INTO if own_p else None


def input_side(members: _Members, mid: Any, addr: Any) -> str | None:
    """Where modifier `mid`'s input reading `addr` sits: a member
    modifier's input from its own lane `INSIDE`, from a rig source `RIG`,
    from a host lane `INTO`; a host modifier reading a member's lane
    `OUT`; None when it touches nothing of the region."""
    own_m = modmod.number(mid) in members.mods
    own_lane = members.own_lane(addr)
    if own_m:
        return INSIDE if own_lane else RIG if _lane(addr) is None else INTO
    return OUT if own_lane else None


# ---------------------------------------------------------------- lift

def _snapshot_entry(m: modmod.Modifier, values: Mapping[str, Any]) -> dict:
    """A modifier's entry with its params at the bases in `values`."""
    bases = {s.key: float(values[modmod.param_id(m.id, s.key)])
             for s in modmod.PARAMS[m.kind] if modmod.param_id(m.id, s.key) in values}
    return m.to_json(bases)


def _desk_row(b: Binding) -> dict:
    d = b.to_json()
    d.pop("layer", None)
    return d


def lift(spec: G.GraphSpec | None, table, values: Mapping[str, Any],
         layout: Mapping[str, Any] | None, node_ids: Iterable[str]
         ) -> tuple[dict, list[str]]:
    """Cut a patch out of a loaded preset's parts — the pure half of *save
    as patch* (P1). `spec` is the landed graph section, `table` the
    `routing.Bindings` (its routes, preset-layer desk, modifiers, macros),
    `values` the registry's snapshot of the performance params, `layout`
    the GRAPH page's positions, `node_ids` the canvas ids picked
    (``render:acid.2``, ``mod.3``, ``lfo.5``, ``env.7``, ``macro.2``).

    Returns ``(doc, refused)``: the file's dict (``schema``, ``name`` and
    ``note`` empty, for the caller to fill) and, in words, every id it left
    out — a frame singleton, an output, the camera or a cloud, a media
    channel, the sequencer, a lane envelope, a copy without its original,
    a host macro's subscriber on a member. The caller says them and saves
    the rest.

    The members are renamed to the lowest ids, as if the patch were alone
    (`acid.2` → `acid`, two acids `acid`, `acid.2` by instance; `mod.3` →
    `mod.1`; `lfo.5` → `lfo.1`; an envelope → `env.6`; a macro keeps its
    number), every id rewritten in the values, wires, rows, modifier
    inputs, subscribers and layout; the layout rebased so its top-left is
    ``(0, 0)``. Every cable crossing the edge is classified: a render wire
    into a member is an inlet port (``was`` its source), out of one an
    outlet (``was`` the port it went into); a row from a rig source onto a
    member is kept verbatim; a row from a member lane onto a host param, or
    from a host lane onto a member, is kept with the host's end as it is
    (a host port, derived at `read`). `values` holds only the members'
    params (D5)."""
    members, refused = select(spec, table, node_ids)
    render = list(members.render)
    entries = {entry_name(e): e for e in (spec.to_json().get("nodes", []) if spec else [])}
    # the lowest ids, as if the patch were alone
    rn = _Renamer(members)
    by_base: dict[str, list[int]] = {}
    for name in render:
        base, n, _ = _family(name)
        if n not in by_base.setdefault(base, []):
            by_base[base].append(n)
    for base, ns in by_base.items():
        first = 2 if base == "hands" else 1
        for k, n in enumerate(sorted(ns)):
            rn.render[(base, n)] = first + k
    rn.voices = {MOD: {n: k + 1 for k, n in enumerate(members.mods)},
                 LFO: {n: k + 1 for k, n in enumerate(members.lfos)},
                 ENV: {n: FIRST_ENV + k for k, n in enumerate(members.envs)},
                 MACRO: {n: n for n in members.macros}}
    # the render graph: entries, internal wires, crossing ports
    nodes = []
    for name in render:
        e = dict(entries.get(name) or _entry_for(name))
        if e.get("kind") == "hands":
            e.pop("laid", None)          # how the frame's one layer is laid: the host's
        nodes.append(rn.entry(e))
    nodes.sort(key=lambda e: entry_name(e) or "")
    wires, ports = [], []
    ins = outs = 0
    for w, where in crossing(spec, render):
        if where == INSIDE:
            wires.append(rn.wire(w.to_json()))
        elif where == INTO:
            ins += 1
            ports.append({"id": _join("in", ins), "type": wire_type(w, where),
                          "to": rn.dst(w.dst), "was": w.src})
        else:
            outs += 1
            ports.append({"id": _join("out", outs), "type": wire_type(w, where),
                          "from": rn.src(w.src), "was": w.dst})
    # the rows: every one that touches a member
    routes = [rn.row(b.to_json()) for b in table.routes()
              if touches(members, b.source, b.target)]
    desk = [rn.row(_desk_row(b)) for b in table.desk() if members.owns(b.target)]
    mods = [rn.modifier(_snapshot_entry(m, values)) for m in getattr(table, "modifiers", ())
            if modmod.number(m.id) in members.mods]
    mods.sort(key=lambda d: modmod.number(d["id"]) or 0)
    macros = {}
    for n in members.macros:
        mid = f"{MACRO}.{n}"
        mac = table.macros.get(mid)
        macros[mid] = rn.macro(mac.to_json() if mac is not None else {"subs": []})
    for mid, mac in sorted(table.macros.items(), key=lambda kv: _macro_n(kv[0])):
        if _macro_n(mid) in members.macros:
            continue
        for s in mac.subs:
            if s.base is not None and members.owns(s.base):
                refused.append(HOST_MACRO_WORDS.format(mid=mid, pid=s.base))
    vals = {rn.param(pid): v for pid, v in values.items()
            if members.owns(pid) and not pid.startswith(modmod.PREFIX)}
    # the layout: the members' own positions, rebased (none: none — no auto layout)
    lay = {}
    for cid in members.canvas():
        xy = (layout or {}).get(cid)
        if xy is not None:
            lay[rn.canvas(cid)] = [float(xy[0]), float(xy[1])]
    if lay:
        x0 = min(p[0] for p in lay.values())
        y0 = min(p[1] for p in lay.values())
        lay = {k: [round(p[0] - x0), round(p[1] - y0)] for k, p in sorted(lay.items())}
    doc = {"schema": SCHEMA, "name": "", "note": "", "nodes": nodes, "wires": wires,
           "values": dict(sorted(vals.items())), "modifiers": mods, "routes": routes,
           "desk": desk, "macros": macros,
           "lfos": sorted(rn.voice(LFO, n) for n in members.lfos),
           "envs": sorted(rn.voice(ENV, n) for n in members.envs),
           "ports": ports, "layout": lay}
    return doc, refused


# ---------------------------------------------------------------- spawn

@dataclass(frozen=True)
class Host:
    """What `spawn` reads of the preset a patch lands in — a small
    read-only view the caller builds (`Host.of` from the live parts):

    - `names`: every render node the host's section has, and the instance
      names a held program keeps (plan 38's `fx.hold`): a spawned node takes
      none of them;
    - `modifiers`: the modifier ids held (a new one is one past the highest,
      `modifiers.next_id`);
    - `next_voice` / `room`: each bank's `next_id()` (its high-water rule)
      and how many voices it may still add (none once its next id is past
      `modbank.MAX_ID`, as `Bank.refusal` says);
    - `macros`: the macros in use — a label or a subscriber in the table, or
      a row whose target is the macro (a macro's value alone is no use: the
      eight knobs always have one);
    - `desk`: the preset layer's desk rows; `routes`: the performer rows
      (`Bindings.owner` for every param is the first enabled performer on it).

    (No registry ids: a route onto a param the host lacks lands dormant, as
    any route does, and is no conflict — nothing here needs to ask.)"""

    names: frozenset[str] = frozenset()
    modifiers: tuple[str, ...] = ()
    next_voice: Mapping[str, int] = field(default_factory=dict)
    room: Mapping[str, int] = field(default_factory=dict)
    macros: frozenset[str] = frozenset()
    desk: tuple[Binding, ...] = ()
    routes: tuple[Binding, ...] = ()

    @classmethod
    def of(cls, spec: G.GraphSpec | None, table, banks: Mapping[str, Any] | None = None,
           held: Iterable[str] = ()) -> Host:
        """The view of a live preset: its landed `spec`, its `table`
        (`routing.Bindings`), its banks by scheme (each with `next_id()`,
        `MAX` and a length) and the held program's instance names. Reads
        only. A bank not handed in starts one past the highest voice id the
        table names (a lane on a row, a modifier input, a depth subscriber)
        and past its default membership (LFO 5, envelope 6) — never on an
        id the host may hold."""
        rows = [*table.routes(), *table.desk()]
        used = {mid for mid, m in table.macros.items() if not m.empty}
        used |= {b.target for b in rows if is_macro(b.target)}
        named: dict[str, int] = {LFO: max(lfomod.LFOs.DEFAULT), ENV: max(LANE_ENVS)}
        addrs = [b.source for b in rows] + [b.when for b in rows if b.when]
        addrs += [a for m in getattr(table, "modifiers", ()) for a in m.inputs if a]
        addrs += [s.depth[0] for m in table.macros.values() for s in m.subs if s.depth]
        for a in addrs:
            hit = _lane(a)
            if hit is not None and hit[0] in named:
                named[hit[0]] = max(named[hit[0]], hit[1])
        nxt = {s: n + 1 for s, n in named.items()}
        room = {s: modbank.MAX for s in named}
        for s, b in (banks or {}).items():
            nxt[s] = int(b.next_id())
            room[s] = (0 if nxt[s] > modbank.MAX_ID
                       else int(getattr(b, "MAX", modbank.MAX)) - len(b))
        return cls(names=spec_names(spec) | frozenset(held),
                   modifiers=tuple(m.id for m in getattr(table, "modifiers", ())),
                   next_voice=nxt, room=room, macros=frozenset(used),
                   desk=tuple(replace(b) for b in table.desk()),
                   routes=tuple(replace(b) for b in table.routes()))

    def owner(self, pid: str) -> Binding | None:
        """`Bindings.owner`: the one performer on `pid`, or None."""
        return next((b for b in self.routes if b.is_performer and b.target == pid), None)


@dataclass(frozen=True)
class Conflict:
    """One collision between a patch's row and the host (P3's sheet, D3),
    with enough for a two-way choice in words:

    - ``"desk"``: a desk control the host's preset layer maps
      (`Binding.overlaps`) — `control_or_source` the control, `host_target`
      the param the host has on it, `patch_target` the patch's;
    - ``"source"``: a one-owner source (`ONE_OWNER`: a hand axis, a pad
      stick) the host already sends onto another param — the same three;
    - ``"target"``: a patch route onto a param another performer owns
      (`Host.owner`) — `control_or_source` the param, `host_target` the
      host's source on it, `patch_target` the patch's source.

    `row` is the patch's row as the `Landing` holds it (renamed), `host_row`
    the host's row it collides with."""

    kind: str
    control_or_source: str
    host_target: str
    patch_target: str
    row: dict
    host_row: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Landing:
    """What spawning a patch into a host adds (`spawn`), renamed and placed,
    for P3 to land through today's doors as one undo step: the rename map
    (only the ids that moved: ``{"acid": "acid.2", "mod.1": "mod.7",
    "lfo.1": "lfo.6"}``), the render `nodes` and internal `wires` (to join
    the host's section), the `values`, the `modifiers` entries, the `routes`
    and `desk` rows (JSON, as a preset holds them), the `macros` (each
    member macro's label and subscribers), the bank voices `lfos` / `envs`,
    the `layout` moved to the drop point, the `group` entry (P2's shape:
    ``{"name", "patch", "nodes", "open": false}`` — **no `id`**: T2 numbers
    groups, the caller adds ``"id": "group.<n>"``), the `ports` with their
    ends renamed (each an open pin: one whose `was` the host lacks is no
    note), the `conflicts` (P3's sheet; empty: land at once), the `wants`
    (the rig-side sources by scheme head — ``cc``, ``hand``, ``axis@p2`` —
    each with the rows and modifier inputs that read it, for P4 to word)
    and the `notes` (a macro with no free number, a bank with no room)."""

    renames: dict[str, str]
    nodes: tuple[dict, ...]
    wires: tuple[dict, ...]
    values: dict[str, Any]
    modifiers: tuple[dict, ...]
    routes: tuple[dict, ...]
    desk: tuple[dict, ...]
    macros: dict[str, dict]
    lfos: tuple[int, ...]
    envs: tuple[int, ...]
    layout: dict[str, list[float]]
    group: dict
    ports: tuple[dict, ...]
    conflicts: tuple[Conflict, ...]
    wants: dict[str, tuple[dict, ...]]
    notes: tuple[str, ...]


def _taken(names: Iterable[str]) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for name in names:
        base, n, _ = _family(name)
        out.setdefault(base, set()).add(n)
    out.setdefault("hands", set()).add(1)        # hands 1: always the frame's
    return out


def _names_dropped(r: Mapping, gone: _Members) -> bool:
    """Does row `r` name a member that did not spawn (its lane, its param)?"""
    return gone.own_lane(r.get("source")) or gone.owns(r.get("target")) or (
        isinstance(r.get("when"), str) and gone.own_lane(r["when"]))


def _sub_dropped(s: Any, gone: _Members) -> bool:
    """Does macro subscriber `s` name a member that did not spawn — a base
    on its param, a depth on a route from its lane or onto its param?"""
    if not isinstance(s, Mapping):
        return True
    if gone.owns(s.get("base")):
        return True
    dep = s.get("depth")
    return isinstance(dep, Mapping) and (gone.own_lane(dep.get("source"))
                                         or gone.owns(dep.get("target")))


def spawn(doc: Mapping, host: Host, at: tuple[float, float] = (0.0, 0.0), *,
          patch: str | None = None) -> Landing:
    """What spawning patch `doc` into `host` at canvas point `at` would add
    — the pure half of *spawn* (P1, P3). Writes nothing.

    Renames, in the patch's order: a render node takes the lowest instance
    of its base the host does not hold (`graphview._new_instance`'s rule:
    `acid` → `acid.2` where the host has `acid`; a hands node and its layer
    and guide move together); a modifier one past the highest the host
    holds (`modifiers.next_id`); an LFO or envelope the bank's next id (its
    high-water rule; an envelope 6 or more), none when the bank is full or
    its ids are used up (a note; its rows and the subscribers on its lane
    not spawned, a modifier input reading it left empty and said — never
    its old number, which would read the host's voice). The lowest free
    instance may be one a host's dormant rows still name (a removed
    `acid.2`'s): they wake with the spawn, as after an add on the canvas.
    Only the patch's own wires land: a crossing is a port, an open pin
    (D2). A value lands only for a member's param (D5). A macro keeps its number when the host
    does not use it, else takes the lowest free of the eight, else is a
    note — ``"macro.2: no free macro — its subscribers not spawned"`` — and
    it, its value and every row onto it stay out, the rest spawned.

    Lists the conflicts (`Conflict`) and the wants; a spawn twice into one
    host has its second copy's rig rows collide with the first's, row by
    row. `patch` is the group's provenance slug (default: the name's)."""
    p = read(doc)
    m = p.members
    rn = _Renamer(m)
    notes: list[str] = []
    gone = {MOD: [], LFO: [], ENV: [], MACRO: []}
    taken = _taken(host.names)
    for name in sorted(m.render, key=lambda x: (_family(x)[0], _family(x)[1])):
        base, n, _ = _family(name)
        if (base, n) in rn.render:
            continue
        hold = taken.setdefault(base, set())
        new = next(k for k in range(1, len(hold) + 2) if k not in hold)
        hold.add(new)
        rn.render[(base, n)] = new
    nxt = modmod.number(modmod.next_id(host.modifiers)) or 1
    rn.voices[MOD] = {n: nxt + k for k, n in enumerate(m.mods)}
    for scheme in VOICES:
        start = int(host.next_voice.get(scheme, 1))
        if scheme == ENV:
            start = max(start, FIRST_ENV)
        room = host.room.get(scheme)
        out = {}
        for k, n in enumerate(m.ids(scheme)):
            why = (f"the {scheme} bank is full" if room is not None and k >= room
                   else f"{scheme} ids are used up ({modbank.MAX_ID} is the highest)"
                   if start + len(out) > modbank.MAX_ID else None)
            if why is not None:
                gone[scheme].append(n)
                notes.append(NO_VOICE_NOTE.format(vid=f"{scheme}.{n}", why=why))
                continue
            out[n] = start + len(out)
        rn.voices[scheme] = out
        rn.gone[scheme] = set(gone[scheme])
    used = set(host.macros)
    mac_map = {}
    for n in m.macros:
        mid = f"{MACRO}.{n}"
        if mid not in used:
            new = n
        else:
            new = next((k for k in range(1, MACROS + 1) if f"{MACRO}.{k}" not in used), None)
        if new is None:
            gone[MACRO].append(n)
            notes.append(NO_MACRO_NOTE.format(mid=mid))
            continue
        used.add(f"{MACRO}.{new}")
        mac_map[n] = new
    rn.voices[MACRO] = mac_map
    lost = _Members((), tuple(gone[MOD]), tuple(gone[LFO]), tuple(gone[ENV]),
                    tuple(gone[MACRO]))
    kept = _Members(m.render, m.mods, tuple(n for n in m.lfos if n not in gone[LFO]),
                    tuple(n for n in m.envs if n not in gone[ENV]),
                    tuple(n for n in m.macros if n not in gone[MACRO]))
    # the rename map: what moved
    renames: dict[str, str] = {}
    for name in m.render:
        if rn.name(name) != name:
            renames[name] = rn.name(name)
    for scheme in (MOD, LFO, ENV, MACRO):
        for n, new in rn.voices[scheme].items():
            if new != n:
                renames[f"{scheme}.{n}"] = f"{scheme}.{new}"
    nodes = tuple(rn.entry(e) for e in p.nodes)
    # only the patch's own wires, both ends members: a crossing is a port, an
    # open pin — never a wire landed by its saved name (D2), whatever the file
    held = set(m.render)
    wires = tuple(rn.wire(w) for w in p.wires
                  if isinstance(w.get("from"), str) and isinstance(w.get("to"), str)
                  and _node_of(w["from"]) in held and w["to"].rpartition(".")[0] in held)
    # D5 for any caller, not only one that ran `check`: a member's params only
    values = {rn.param(k): v for k, v in p.values.items() if m.owns(k) and not lost.owns(k)}
    mods = []
    for x in p.modifiers:
        y = rn.modifier(x)
        ins = x.get("in")
        for i, a in enumerate([ins] if isinstance(ins, str) else list(ins or ())):
            if a and lost.own_lane(a):
                hit = _lane(a)
                notes.append(NO_INPUT_NOTE.format(mid=y.get("id"), k=i + 1,
                                                  vid=f"{hit[0]}.{hit[1]}"))
        mods.append(y)
    mods = tuple(mods)
    routes = tuple(rn.row(r) for r in p.routes if not _names_dropped(r, lost))
    desk = tuple(rn.row(r) for r in p.desk if not _names_dropped(r, lost))
    macros = {}
    for k, v in p.macros.items():
        if _macro_n(k) in gone[MACRO]:
            continue
        subs = [s for s in v.get("subs") or () if not _sub_dropped(s, lost)]
        macros[f"{MACRO}.{rn.voice(MACRO, _macro_n(k))}"] = rn.macro({**v, "subs": subs})
    lfos = tuple(rn.voice(LFO, n) for n in kept.lfos)
    envs = tuple(rn.voice(ENV, n) for n in kept.envs)
    ax, ay = float(at[0]), float(at[1])
    lay_ok = set(kept.canvas())
    layout = {rn.canvas(cid): [round(xy[0] + ax), round(xy[1] + ay)]
              for cid, xy in p.layout.items() if cid in lay_ok}
    canvas = [rn.canvas(cid) for cid in kept.canvas()]
    group = {"name": p.name, "patch": slug(p.name) if patch is None else patch,
             "nodes": canvas, "open": False}
    ports = tuple(rn.port(x) for x in p.ports)
    # the conflicts (D3): against the host as it stands
    conflicts: list[Conflict] = []
    for r in desk:
        b = Binding.from_json({**r, "layer": "preset"})
        hit = next((h for h in host.desk if b.overlaps(h)), None)
        if hit is not None:
            conflicts.append(Conflict("desk", b.source, hit.target, b.target, dict(r),
                                      _desk_row(hit)))
    for r in routes:
        b = Binding.from_json(r)
        if not b.is_performer:
            continue
        if base_scheme(b.head) in ONE_OWNER:
            hit = next((h for h in host.routes if h.is_performer and h.source == b.source
                        and h.target != b.target), None)
            if hit is not None:
                conflicts.append(Conflict("source", b.source, hit.target, b.target, dict(r),
                                          hit.to_json()))
                continue
        owner = host.owner(b.target)
        if owner is not None:
            conflicts.append(Conflict("target", b.target, owner.source, b.source, dict(r),
                                      owner.to_json()))
    # the wants: every rig-side source, by its scheme head (qualifier kept)
    wants: dict[str, list[dict]] = {}
    own = _Members(kept.render, tuple(rn.voice(MOD, n) for n in kept.mods), lfos, envs,
                   tuple(rn.voice(MACRO, n) for n in kept.macros))
    for r in (*routes, *desk):
        src = r.get("source")
        if isinstance(src, str) and _lane(src) is None and not own.own_lane(src):
            wants.setdefault(Binding.from_json(r).head, []).append(dict(r))
    for x in mods:
        ins = x.get("in")
        for a in ([ins] if isinstance(ins, str) else list(ins or ())):
            if a and _lane(a) is None:
                wants.setdefault(Binding(a, "").head, []).append(
                    {"source": a, "modifier": x.get("id")})
    return Landing(renames=renames, nodes=nodes, wires=wires, values=values, modifiers=mods,
                   routes=routes, desk=desk, macros=macros, lfos=lfos, envs=envs,
                   layout=layout, group=group, ports=ports, conflicts=tuple(conflicts),
                   wants={k: tuple(v) for k, v in wants.items()}, notes=tuple(notes))


def is_rig_source(addr: str) -> bool:
    """Is `addr` a rig-side source — not a modulation lane (``mod:``,
    ``lfo:``, ``env:``)? Open-ended, as `routing.is_continuous` is: any
    other scheme, a ``cc:`` or an OSC role, qualified or not."""
    return _lane(addr) is None


__all__ = ["INSIDE", "INTO", "KIND", "OUT", "RIG", "SCHEMA", "Conflict", "Host", "Landing",
           "Patch", "check", "crossing", "entry_name", "held_words", "input_side",
           "is_rig_source", "lift", "read", "select", "side", "slug", "spawn", "spec_names",
           "sub_side", "touches", "wire_type"]
