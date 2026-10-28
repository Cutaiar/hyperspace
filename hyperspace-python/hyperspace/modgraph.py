"""The modulation graph as data, and the order it is evaluated in (plan 28 N0).

Every performer row, macro subscriber, `scale`, LFO knob and modifier
input is an edge between nodes; `Router.build_modgraph` (routing.py) makes the
graph from the table, and `Router.modulate` runs it in `order(g)`, so
a value that something else in the pass reads — an LFO's depth a hand
owns, a macro scaling a push, a `scale` param that is itself modulated —
lands **this frame**, before its reader (decision 7: the one-frame lag
is gone). Nothing reads a stale value but through a `delay` modifier.

Until plan 40 this module was named `patch` (`Patch`, `PatchNode`, `PatchEdge`)
(D1): "patch" is now the owner's word for a saved group of nodes and its
boundary (`patches.py`); this is the modulation graph, `Router.modgraph`.

Nodes (`ModNode.kind`):

  source    a fed lane: ``lane:0``, ``hand:right.y``, ``axis:2``, ``ext:1``,
            an OSC role's axis — its id is the address a row names
  lfo       an LFO (``lfo:0`` is LFO 1): a source *with inputs*, its knob
            params; it steps inside the pass
  modifier  a modifier (N1), ``mod:<n>``: inputs in, one lane out. A
            `delay` modifier (``delay=True``) is where a loop may close
  macro     ``macro.N``: a param whose subscribers fan out into other
            params' `base` and other cables' `depth`
  param     a registry param, with a `base` port and a `mod` port

Edges (`ModEdge.port`, the port on `dst`):

  mod       a performer row: source → param. ``cable`` is the row's
            identity, ``(source, target)`` — routes convert one-to-one
  when      a row's gate: the gate's source → the row's param
  depth     a cable's depth: a `scale` param, or a macro's depth
            subscriber → the param the cable lands on (``cable`` names it)
  base      a macro's base subscriber → its param. Drawn, never ordered:
            the subscribers are scene-setters that ran before the pass
            (`Router.follow_macros`, frame step 3), so they put no
            constraint on the pass and close no loop
  in        a modifier's input (N1): a lane → the modifier
  shape rate sync depth phase reset trigger
            an LFO knob param → its LFO (``lfo.trigger`` → every LFO);
            on a modifier, its own param's name (``mod.2.attack``)

An edge orders the pass (`ordering`) when it is `enabled`, is not a
`base` edge, and does not close a loop into a delay node: an edge into a
delay orders like any other — a plain delay runs after its input, so it
holds this frame's reading for the next — unless the delay reaches that
edge's source again, and then the delay runs first and emits what it held
(the loop's one frame). `cycles` lists the loops over the ordering edges:
a loop through a delay is no loop.

Pure data and pure functions; imports nothing from the package but the
leaves `motion` and `tapers` (none needed yet), like `graph.py`'s sorter
this mirrors (`Graph._sort`: dependencies first, ties in insertion order).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# a modulator bank's voices (plan 31 B) take the bank's scheme as their
# kind — ``lfo``, ``env`` — and routing.BANKS says which schemes those are
KINDS = ("source", "lfo", "env", "modifier", "macro", "param")
# plan 30 D2: the render graph's port type for a value a node publishes
# once a frame (`graph.VALUE`; named here, not imported: this module is a
# leaf). A render node's `VALUE` port would be a `source` here, its id the
# node's port (``palette:palette``) — none publishes one yet
RENDER_VALUE = "value"
# the ports an LFO's knob params feed, in the order lfo.py declares them,
# then the bank's global trigger
LFO_KNOBS = ("shape", "rate", "sync", "depth", "phase", "reset")
LFO_PORTS = (*LFO_KNOBS, "trigger")
# the ports an envelope's params feed (plan 31 W1): its knobs in the order
# envelope.py declares them, then `fire` and `gate` (envelope.Envelopes.KNOBS)
ENV_KNOBS = ("mode", "attack", "hold", "decay", "sustain", "release", "curve", "sync",
             "retrig", "amount", "velocity", "fire", "gate")
PORTS = tuple(dict.fromkeys(("mod", "when", "depth", "base", "in", *LFO_PORTS, *ENV_KNOBS)))
# the ports that never order the pass (see the module docstring)
UNORDERED = frozenset({"base"})
# `cycles` stops listing past this many loops: a pathological table is
# refused loop by loop anyway (Router.build_modgraph cuts one and asks again)
MAX_CYCLES = 256


@dataclass(frozen=True)
class ModNode:
    """One node. `id` is the address a row names for a source, an LFO or a
    modifier (``lane:0``, ``lfo:1``, ``mod:3``) and the param id for a
    param or a macro (``view.bright``, ``macro.2``) — the two never meet:
    an address has a ``:``, an id never does."""
    id: str
    kind: str
    delay: bool = False      # a `delay` modifier: a loop may close through it


@dataclass(frozen=True)
class ModEdge:
    """`src` → `dst`, into `dst`'s `port`. `cable` is the performer row the
    edge belongs to — ``(source, target)`` — for a `mod`, `when` or `depth`
    edge; None for the rest. A disabled edge (a row switched off, or the
    cable `Router.build_modgraph` cut to break a loop) is drawn but does not
    order or run."""
    src: str
    dst: str
    port: str
    cable: tuple[str, str] | None = None
    enabled: bool = True


@dataclass
class ModGraph:
    """Nodes in insertion order (a dict by id) and edges in insertion order."""
    nodes: dict[str, ModNode] = field(default_factory=dict)
    edges: list[ModEdge] = field(default_factory=list)

    def add(self, node_id: str, kind: str, *, delay: bool = False) -> ModNode:
        """The node `node_id`, added at the end unless it is there already
        (then the first kind given stands)."""
        n = self.nodes.get(node_id)
        if n is None:
            n = self.nodes[node_id] = ModNode(node_id, kind, delay)
        return n

    def link(self, src: str, dst: str, port: str, cable: tuple[str, str] | None = None,
             enabled: bool = True) -> ModEdge:
        e = ModEdge(src, dst, port, cable, enabled)
        self.edges.append(e)
        return e

    def into(self, node_id: str) -> list[ModEdge]:
        return [e for e in self.edges if e.dst == node_id]

    def out_of(self, node_id: str) -> list[ModEdge]:
        return [e for e in self.edges if e.src == node_id]


def _live(g: ModGraph, e: ModEdge) -> bool:
    """An edge that could order: enabled, not `base`, between two nodes."""
    return (e.enabled and e.port not in UNORDERED
            and e.src in g.nodes and e.dst in g.nodes)


def ordering(g: ModGraph) -> list[ModEdge]:
    """The edges that constrain the pass — `e.src` runs before `e.dst` —
    in edge order: every live edge but one into a delay node that the
    delay itself reaches back to (that edge closes a loop through the
    delay, which is where the loop takes its one frame)."""
    live = [e for e in g.edges if _live(g, e)]
    delays = {n for n, node in g.nodes.items() if node.delay}
    if not delays:
        return live
    succ: dict[str, list[str]] = {}
    for e in live:
        succ.setdefault(e.src, []).append(e.dst)

    def reach(start: str) -> set[str]:
        seen, todo = set(), [start]
        while todo:
            for nxt in succ.get(todo.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
        return seen

    back = {d: reach(d) for d in delays}
    return [e for e in live if e.dst not in delays or e.src not in back[e.dst]]


def orders(g: ModGraph, e: ModEdge) -> bool:
    """Does edge `e` constrain the pass? (`ordering`, for one edge.)"""
    return any(x is e for x in ordering(g))


def _deps(g: ModGraph) -> dict[str, list[str]]:
    """node id → the ids it reads, in edge order, each once."""
    deps: dict[str, list[str]] = {n: [] for n in g.nodes}
    for e in ordering(g):
        if e.src not in deps[e.dst]:
            deps[e.dst].append(e.src)
    return deps


def order(g: ModGraph) -> list[ModNode]:
    """Every node, each after everything it reads: a depth-first walk in
    insertion order, dependencies first, ties left in insertion order (as
    `graph.Graph._sort`). On a loop the walk does not go round again — a
    node already on the walk's path is taken as done — so it always ends;
    `Router.build_modgraph` cuts every loop before it asks."""
    deps = _deps(g)
    done: list[ModNode] = []
    seen: set[str] = set()

    def visit(nid: str) -> None:
        if nid in seen:
            return
        seen.add(nid)
        for d in deps[nid]:
            visit(d)
        done.append(g.nodes[nid])

    for nid in g.nodes:
        visit(nid)
    return done


def cycles(g: ModGraph) -> list[list[str]]:
    """Every loop over the ordering edges, each as its node ids from the
    loop's earliest node (in insertion order) round to the node before it
    comes back; a loop through a delay modifier is none (its edge in does
    not order). Each elementary loop once, in a stable order; at most
    `MAX_CYCLES`."""
    ids = list(g.nodes)
    rank = {n: i for i, n in enumerate(ids)}
    succ: dict[str, list[str]] = {n: [] for n in ids}
    for e in ordering(g):
        if e.dst not in succ[e.src]:
            succ[e.src].append(e.dst)
    found: list[list[str]] = []
    for start in ids:
        # the loops whose earliest node is `start`: a walk over later nodes
        r0 = rank[start]
        path, on = [start], {start}
        stack = [iter(succ[start])]
        while stack and len(found) < MAX_CYCLES:
            nxt = next(stack[-1], None)
            if nxt is None:
                stack.pop()
                on.discard(path.pop())
                continue
            if nxt == start:
                found.append(list(path))
            elif rank[nxt] > r0 and nxt not in on:
                path.append(nxt)
                on.add(nxt)
                stack.append(iter(succ[nxt]))
    return found
