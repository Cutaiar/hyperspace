"""modgraph.py (plan 28 N0): the modulation graph as data, its order and its
loops — proved without a Router, then the edges `Router.build_modgraph`
makes from a route, a macro subscriber and a scale."""

import ast
import math
from pathlib import Path

import numpy as np
import pytest

from hyperspace import modgraph as P
from hyperspace.bands import CEIL
from hyperspace.params import Registry
from hyperspace.routing import Binding, Bindings, Macro, Router, Sub

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


def _ids(nodes):
    return [n.id for n in nodes]


def test_order_puts_dependencies_first_and_keeps_insertion_order_for_ties():
    g = P.ModGraph()
    for nid, kind in [("view.bright", "param"), ("lane:0", "source"), ("lfo:0", "lfo"),
                      ("lfo.1.depth", "param"), ("hand:right.y", "source"),
                      ("fx.mix", "param"), ("macro.1", "macro")]:
        g.add(nid, kind)
    g.link("lfo:0", "view.bright", "mod", ("lfo:0", "view.bright"))
    g.link("lfo.1.depth", "lfo:0", "depth")
    g.link("hand:right.y", "lfo.1.depth", "mod", ("hand:right.y", "lfo.1.depth"))
    g.link("lane:0", "fx.mix", "mod", ("lane:0", "fx.mix"))
    g.link("macro.1", "fx.mix", "depth", ("lane:0", "fx.mix"))
    g.link("macro.1", "view.bright", "base")       # a scene-setter: never orders
    got = _ids(P.order(g))
    assert got == ["hand:right.y", "lfo.1.depth", "lfo:0", "view.bright", "lane:0",
                   "macro.1", "fx.mix"]
    for e in g.edges:                                # every ordering edge points forward
        if P.orders(g, e):
            assert got.index(e.src) < got.index(e.dst), e
    # no edges: insertion order exactly, and a node added twice stays put
    h = P.ModGraph()
    for nid in ["c", "a", "b", "a"]:
        h.add(nid, "param")
    assert _ids(P.order(h)) == ["c", "a", "b"]
    # a disabled edge does not order: the tie stays in insertion order
    h.link("b", "c", "mod", ("b", "c"), enabled=False)
    assert _ids(P.order(h)) == ["c", "a", "b"]
    h.link("b", "c", "mod", ("b", "c"))
    assert _ids(P.order(h)) == ["b", "c", "a"]


def test_cycles_finds_every_loop_and_none_through_a_delay():
    g = P.ModGraph()
    for nid, kind in [("lfo:0", "lfo"), ("lfo.1.depth", "param"), ("lfo:1", "lfo"),
                      ("lfo.2.rate", "param"), ("view.bright", "param")]:
        g.add(nid, kind)
    # LFO 1 drives its own depth: a loop of two
    g.link("lfo:0", "lfo.1.depth", "mod", ("lfo:0", "lfo.1.depth"))
    g.link("lfo.1.depth", "lfo:0", "depth")
    # LFO 1 → LFO 2's rate → LFO 2 → LFO 1's depth: a loop of four through lfo:0
    g.link("lfo.2.rate", "lfo:1", "rate")
    g.link("lfo:0", "lfo.2.rate", "mod", ("lfo:0", "lfo.2.rate"))
    g.link("lfo:1", "lfo.1.depth", "when", ("lfo:0", "lfo.1.depth"))
    g.link("lfo:1", "view.bright", "mod", ("lfo:1", "view.bright"))   # a leaf: no loop
    assert P.cycles(g) == [["lfo:0", "lfo.1.depth"],
                           ["lfo:0", "lfo.2.rate", "lfo:1", "lfo.1.depth"]]
    # a base subscriber never closes a loop
    g.add("macro.1", "macro")
    g.link("lfo:1", "macro.1", "mod", ("lfo:1", "macro.1"))
    g.link("macro.1", "lfo.2.rate", "base")
    assert len(P.cycles(g)) == 2
    # through a delay modifier: no loop at all
    d = P.ModGraph()
    d.add("hand:right.x", "source")
    d.add("mod:1", "modifier")
    d.add("mod:2", "modifier", delay=True)
    d.add("mod.1.mul", "param")
    d.link("hand:right.x", "mod:1", "in")
    d.link("mod:1", "mod.1.mul", "mod", ("mod:1", "mod.1.mul"))
    d.link("mod.1.mul", "mod:1", "mul")
    assert P.cycles(d) == [["mod:1", "mod.1.mul"]]
    m2 = P.ModGraph()                                      # two modifiers, no cable: still a loop
    m2.add("mod:1", "modifier")
    m2.add("mod:2", "modifier")
    m2.link("mod:2", "mod:1", "in")
    m2.link("mod:1", "mod:2", "in")
    assert P.cycles(m2) == [["mod:1", "mod:2"]]
    d2 = P.ModGraph()
    d2.add("mod:1", "modifier")
    d2.add("mod:2", "modifier", delay=True)
    d2.add("mod.1.mul", "param")
    d2.link("mod:1", "mod:2", "in")                     # mod 1 → delay → mul → mod 1
    d2.link("mod:2", "mod.1.mul", "mod", ("mod:2", "mod.1.mul"))
    d2.link("mod.1.mul", "mod:1", "mul")
    assert P.cycles(d2) == []
    assert _ids(P.order(d2)) == ["mod:2", "mod.1.mul", "mod:1"]   # the delay emits first
    # a delay closing no loop runs after its input, like any node
    d3 = P.ModGraph()
    d3.add("mod:2", "modifier", delay=True)
    d3.add("view.bright", "param")
    d3.add("hand:right.x", "source")
    d3.link("hand:right.x", "mod:2", "in")
    d3.link("mod:2", "view.bright", "mod", ("mod:2", "view.bright"))
    assert _ids(P.order(d3)) == ["hand:right.x", "mod:2", "view.bright"]
    assert P.cycles(d3) == []
    # a cut cable (disabled) breaks its loop
    e = P.ModGraph()
    e.add("lfo:0", "lfo")
    e.add("lfo.1.depth", "param")
    e.link("lfo:0", "lfo.1.depth", "mod", ("lfo:0", "lfo.1.depth"), enabled=False)
    e.link("lfo.1.depth", "lfo:0", "depth")
    assert P.cycles(e) == []
    assert _ids(P.order(e)) == ["lfo.1.depth", "lfo:0"]


def test_a_route_a_macro_sub_and_a_scale_are_the_edges_the_design_names():
    reg = Registry()
    for pid in ("view.bright", "fx.mix", "master.gain", "lfo.1.depth", "macro.1",
                "view.speed"):
        reg.continuous(pid, pid, lambda: 0.5, lambda v: None)
    table = Bindings([
        Binding("lane:0", "view.bright", "push", 0.5, scale="master.gain"),
        Binding("hand:right.y", "lfo.1.depth", "position"),
        Binding("lfo:0", "fx.mix", "push", 0.3, when="hand:right.pinch.index"),
        Binding("lane:1", "view.speed", "push", 0.2, enabled=False),
    ])
    table.macros = {"macro.1": Macro("m", [Sub(depth=("lfo:0", "fx.mix")),
                                           Sub(base="view.speed", lo=0.5, hi=0.25)])}
    router = Router(reg, table)
    g = router.build_modgraph()
    kinds = {n.id: n.kind for n in g.nodes.values()}
    assert kinds == {
        "lane:0": "source", "view.bright": "param", "master.gain": "param",
        "hand:right.y": "source", "lfo.1.depth": "param",
        "lfo:0": "lfo", "fx.mix": "param", "hand:right.pinch.index": "source",
        "macro.1": "macro", "lane:1": "source", "view.speed": "param",
    }
    edges = {(e.src, e.dst, e.port, e.cable, e.enabled) for e in g.edges}
    assert edges == {
        # a route: source → param `mod`, its identity (source, target)
        ("lane:0", "view.bright", "mod", ("lane:0", "view.bright"), True),
        # its scale: param → that cable's depth
        ("master.gain", "view.bright", "depth", ("lane:0", "view.bright"), True),
        ("hand:right.y", "lfo.1.depth", "mod", ("hand:right.y", "lfo.1.depth"), True),
        # an LFO knob: param → LFO
        ("lfo.1.depth", "lfo:0", "depth", None, True),
        ("lfo:0", "fx.mix", "mod", ("lfo:0", "fx.mix"), True),
        ("hand:right.pinch.index", "fx.mix", "when", ("lfo:0", "fx.mix"), True),
        # a macro's depth subscriber: macro → that cable's depth
        ("macro.1", "fx.mix", "depth", ("lfo:0", "fx.mix"), True),
        # a macro's base subscriber: macro → param `base`
        ("macro.1", "view.speed", "base", None, True),
        # a switched-off row is drawn, not run
        ("lane:1", "view.speed", "mod", ("lane:1", "view.speed"), False),
    }
    # one cable per route: the table's rows and the patch's mod edges agree
    mods = [e.cable for e in g.edges if e.port == "mod"]
    assert mods == [(b.source, b.target) for b in table.routes()]
    order = _ids(P.order(g))
    assert order.index("lfo.1.depth") < order.index("lfo:0") < order.index("fx.mix")
    assert order.index("master.gain") < order.index("view.bright")
    assert router.modgraph is router.modgraph                 # cached, not rebuilt per read


def test_modgraph_is_a_leaf():
    """Like graph.py: modgraph.py imports nothing from the package but the
    leaves `motion` and `tapers` (plan 28 N0)."""
    tree = ast.parse((PKG / "modgraph.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level:
            assert (node.module or "").split(".")[0] in ("motion", "tapers"), node.module
        if isinstance(node, ast.ImportFrom) and not node.level:
            assert not (node.module or "").startswith("hyperspace"), node.module
        if isinstance(node, ast.Import):
            assert all(not a.name.startswith("hyperspace") for a in node.names)


def test_a_param_the_pass_lands_is_applied_once_a_frame():
    """`Param.apply` is idempotent within a frame (plan 28 N0): a param
    `Router.modulate` lands early — a `scale` a lane's push reads — is
    skipped by `reg.apply()`, so it is not let go and its offset not
    doubled; a toggle nothing reads lands in `reg.apply()` once. An
    `apply` with no pass before it lands everything, as before."""
    state = {"gain": 0.5, "on": False, "bright": 0.5}

    def put(k):
        return lambda v: state.__setitem__(k, v)

    reg = Registry()
    gain = reg.continuous("master.gain", "gain", lambda: state["gain"], put("gain"))
    on = reg.toggle("view.faces", "faces", lambda: state["on"], put("on"))
    bright = reg.continuous("view.bright", "bright", lambda: state["bright"], put("bright"))
    table = Bindings([Binding("hand:0", "master.gain", "position"),
                      Binding("hand:1", "view.faces", "position"),
                      Binding("lfo:0", "view.bright", "push", 1.0, scale="master.gain")])
    router = Router(reg, table)
    router.modgraph                                       # noqa: B018 — builds the plan
    landed = [s[1] for s in router.__dict__["_plan"] if s[0] == "param" and s[3]]
    assert landed == ["master.gain"]                   # read by the push: lands in the pass
    router.feed("hand", [0.8, 1.0])
    router.feed("lfo", [0.75])
    router.rests["lfo"] = [0.5]
    calls: list[str] = []
    for p in (gain, on, bright):
        def spy(mark=None, orig=p.apply, pid=p.id):
            calls.append(pid)
            orig(mark)
        p.apply = spy
    router.modulate()
    assert state["gain"] == pytest.approx(0.8) and gain.modulated   # before the push read it
    assert calls == ["master.gain"]
    reg.apply()
    assert gain.modulated and state["gain"] == pytest.approx(0.8)   # not let go a second time
    assert state["on"] is True and on.modulated
    assert state["bright"] == pytest.approx(0.5 + 0.8 * 0.25)       # × this frame's gain, once
    assert calls.count("master.gain") == 2 and calls.count("view.faces") == 1
    reg.apply()                                        # no pass before it: lands everything
    assert not gain.modulated and state["gain"] == pytest.approx(0.5)


def _mod_rig():
    """A bare registry with the two params the routes below land on, a
    table, a router: N1's modifiers added through the table's own door."""
    from types import SimpleNamespace

    state = {"view.bright": 0.5, "lfo.1.depth": 0.5, "master.gain": 0.5}
    reg = Registry()
    for pid in state:
        reg.continuous(pid, pid, lambda k=pid: state[k],
                       lambda v, k=pid: state.__setitem__(k, v))
    table = Bindings()
    router = Router(reg, table)
    lane = lambda u: SimpleNamespace(lanes=np.array([u * CEIL, 0.0]))
    return reg, table, router, lane


def test_a_modifier_node_runs_in_order_and_its_params_land_first():
    """N1's modifiers are `modifier` nodes at ``mod:<n>``: inputs as `in`
    edges, their own params (``mod.1.mul``) as edges by name, so a route on
    a modifier's param lands before the modifier steps — the same frame,
    even the frame `set_modifiers` re-declared every ``mod.*`` param (N1's
    concern 4: no frame on the bases). A route from ``mod:1`` is an edge
    from the modifier node."""
    reg, table, router, lane = _mod_rig()
    table.add_modifier("scale", ["lane:0"], reg)
    table.add(Binding("hand:right.y", "mod.1.mul", "position"))
    table.add(Binding("mod:1", "view.bright", "push", 0.5))
    router.names["hand"] = {"right.y": 0}
    router.feed("hand", [0.75])                         # mul = −4 + 8 · 0.75 = 2
    g = router.modgraph
    assert g.nodes["mod:1"].kind == "modifier"
    edges = {(e.src, e.dst, e.port) for e in g.edges}
    assert {("lane:0", "mod:1", "in"), ("mod.1.mul", "mod:1", "mul"),
            ("mod:1", "view.bright", "mod")} <= edges
    order = _ids(P.order(g))
    assert order.index("mod.1.mul") < order.index("mod:1") < order.index("view.bright")
    router.modulate(lane(0.4))
    reg.apply()
    assert router.feeds["mod"][1] == pytest.approx(0.8)  # × the hand's 2, this frame
    # a second modifier re-declares every mod.* param: still this frame's mul
    table.add_modifier("delay", ["mod:1"], reg)
    router.modulate(lane(0.3))
    assert router.feeds["mod"][1] == pytest.approx(0.6)
    assert router.feeds["mod"][2] == pytest.approx(0.0)  # a plain delay: its rest first…
    reg.apply()
    router.modulate(lane(0.1))
    assert router.feeds["mod"][2] == pytest.approx(0.6)  # …then its input, one frame on


def test_a_loop_through_a_delay_runs_exactly_one_frame_late():
    """`cycles` sees no loop through a delay, end to end: mod.1 adds band 0
    to mod.2, mod.2 delays mod.1 — no cut, no note, the delay runs first
    and emits mod.1's lane as it stood (its rest on the first frame), so
    mod.1 climbs by band 0 a frame."""
    reg, table, router, lane = _mod_rig()
    table.add_modifier("combine", ["lane:0", "mod:2"], reg)          # add
    table.add_modifier("delay", ["mod:1"], reg)
    assert P.cycles(router.modgraph) == [] and router.modgraph_notes == []
    assert _ids(P.order(router.modgraph)).index("mod:2") < _ids(P.order(router.modgraph)).index("mod:1")
    seen = []
    for _ in range(4):
        router.modulate(lane(0.1))
        reg.apply()
        seen += [float(router.feeds["mod"][1]), float(router.feeds["mod"][2])]
    assert seen == pytest.approx([0.1, 0.0, 0.2, 0.1, 0.3, 0.2, 0.4, 0.3])


def test_a_loop_of_modifiers_alone_keeps_its_last_input_off_with_a_note():
    """A loop with no cable on it (two modifiers reading each other) keeps
    the last modifier's input on it off, in id order — that modifier
    dormant — with a note; the next loop (a cable one) is cut too."""
    reg, table, router, lane = _mod_rig()
    table.add_modifier("scale", ["mod:2"], reg)
    table.add_modifier("scale", ["mod:1"], reg)
    table.add(Binding("lfo:0", "lfo.1.depth", "push", 0.5))          # LFO 1 on its own depth
    notes = router.modgraph_notes
    assert notes == [
        "loop: mod:1 → mod:2 → mod:1 needs a delay — mod.2's input mod:1 is off until it has one",
        ("loop: lfo:0 → lfo.1.depth → lfo:0 needs a delay — lfo:0 → lfo.1.depth is off "
         "until it has one")]
    assert router.modgraph_cut == {("mod:1", "mod:2"), ("lfo:0", "lfo.1.depth")}
    assert P.cycles(router.modgraph) == []
    router.feed("lfo", [0.9])
    router.rests["lfo"] = [0.5]
    router.modulate(lane(0.4))
    reg.apply()
    vec = router.feeds["mod"]
    assert math.isnan(vec[2]) and math.isnan(vec[1])     # dormant, both
    assert not reg["lfo.1.depth"].modulated


def test_a_loop_through_a_scale_or_a_macro_depth_sub_is_cut():
    """The sorter sees a loop through a `scale` param and through a macro's
    depth subscriber; the later row in table order is cut."""
    reg = Registry()
    for pid in ("master.gain", "lfo.1.depth", "macro.1"):
        reg.continuous(pid, pid, lambda: 0.5, lambda v: None)
    a = Binding("lfo:0", "master.gain", "push", 0.5)
    b = Binding("lane:0", "lfo.1.depth", "push", 0.5, scale="master.gain")
    router = Router(reg, Bindings([a, b]))
    assert P.cycles(router.build_modgraph()) == [["lfo:0", "master.gain", "lfo.1.depth"]]
    assert router.modgraph_cut == {("lane:0", "lfo.1.depth")}
    c = Binding("lfo:0", "macro.1", "push", 0.5)
    d = Binding("lane:0", "lfo.1.depth", "push", 0.5)
    table = Bindings([c, d])
    table.macros = {"macro.1": Macro("", [Sub(depth=("lane:0", "lfo.1.depth"))])}
    router = Router(reg, table)
    assert P.cycles(router.build_modgraph()) == [["lfo:0", "macro.1", "lfo.1.depth"]]
    assert router.modgraph_cut == {("lane:0", "lfo.1.depth")}
