"""Plan 35 T4: the retired switch states as wiring, for the tests.

The pipelines are gone: a frame is its wires (`graph.build_graph`), and
what an output's three switches used to give it — the scene, the hands
over, the hands through the effects — is that output's own wires over All
outputs' (`graphmigrate.output_wires`, `Shows`). The golden tool draws its
states so (`tools/golden_frames.py`, `rig_section`), and the frame
signatures prove it node for node against the retired `default_graph`
(`tests/fixtures/frame-signatures.json`). These helpers say a test's
switch states the same way: every window's mutes on, each state its
output's wiring.

    graph([Shows(), Shows(through=True)], src, effects=("acid",))
    r.wiring = wiring(r.wiring, Shows(), Shows(scene=False, through=True))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace.outputs import Switches, View

Shows = M.Shows


def section(src: Any = None, **kw) -> dict:
    """`src` as a wired frame's section: a `Wiring` (unwired: as a load
    wires it, `graphmigrate.wired_of`; None, the factory look), a section
    dict or `GraphSpec` before the wired frame (renamed and wired, as the
    load's migration does), or a wired one as it is."""
    if src is None:
        src = G.Wiring()
    if isinstance(src, G.Wiring):
        if src.wired:
            # (plan 36 T3: `wiring_of` and a renderer hand a wired one —
            # its section is its wires, as the canvas reads it)
            return G.GraphSpec(
                hands=tuple(src.nodes()),
                laid=src.blend, laid_on=src.laid_on,
                others=(*(("composite", c) for c in src.composites),
                        *(("copy", c) for c in src.copies)),
                wires=tuple(src.wires), wired=True).to_json()
        # (plan 36 T3: D1's placements are written as wires in `shown`,
        # after the states — the builder placed on each output's state)
        return M.wired_of(src, placements=False)
    if isinstance(src, G.GraphSpec):
        src = src.to_json()
    if src.get(G.FRAME_KEY) == G.WIRED_FRAME:
        return src
    if not has_frame_run(G.read_graph(src)):
        # (a section from before plan 33's run: the load's migration, which
        # writes each wire D1 would write short as the entry it stood for)
        values = {"backdrop.history": True} if kw.get("backdrop_history") else {}
        doc, _ = M.migrate({"values": values, "graph": src}, {})
        return doc["graph"]
    return M.wired_section(M.renamed(src), G.read_graph(src), **kw)


def old_style(sec: Any) -> bool:
    """Whether a wired section is in the words before plan 36 T4: its
    look-back recording `lookback.capture`, or plan 34's `echo.<k>` nodes —
    what the migration's last step rewrites (`graphmigrate.split_lookback`)."""
    if not isinstance(sec, dict):
        return False
    return (any(isinstance(w, dict) and w.get("to") == "lookback.capture"
                for w in sec.get("wires") or [])
            or any(isinstance(n, dict) and n.get("kind") == "echo"
                   for n in sec.get("nodes") or []))


def shown(src: Any = None, *shows: Shows, look: str = "off", **kw) -> dict:
    """`section(src)` with output k's overrides for `shows[k - 1]` — and
    (plan 36 T4) an old-style look-back split last, as `look` says the old
    values had it (`graphmigrate.look_of`: "off" draws none)."""
    sec = section(src, **kw)
    for k, sh in enumerate(shows):
        if sh != Shows():
            sec = M.with_output_wires(sec, k + 1, sh)
    out = M.placed_wires(sec)
    return M.split_lookback(out, look) if old_style(out) else out


def wiring(src: Any = None, *shows: Shows, **kw) -> G.Wiring:
    """The wired `Wiring` of `shown(src, *shows)` — what a renderer is
    handed (`Renderer.wiring`); every window's mutes on."""
    got = G.read_graph(shown(src, *shows, **kw))
    assert not got.notes, got.notes
    return got.wiring()


@dataclass
class Thru:
    """A window whose state is wired (the retired `Switches(through=True)`,
    and any other `Shows` with the window's own look): its picture, its
    hands, through the effects or not — written into the renderer's wiring
    (`wire_switches`) — and the window's dim and mirror, every mute on."""

    scene: bool = True
    hands: bool = True
    through: bool = True
    dim: float = 1.0
    flip_x: bool = False
    flip_y: bool = False

    @property
    def shows(self) -> Shows:
        return Shows(self.scene, self.hands, self.through)


def wire_switches(r, *states) -> list[Switches]:
    """Renderer `r` wired for `states` — each a `Thru` or a `Switches`
    (the retired switches' scene and hands), its output's wiring, as the
    golden rig draws its states — over its own unwired wiring (kept on `r`
    the first time, so a second call wires the same base); the windows'
    `Switches`: their dim and mirror, every mute on."""
    base = getattr(r, "_wiredframe_base", None)
    if base is None or getattr(r.wiring, "wired", False) is False:
        # (plan 36 T3: a renderer's own wiring is the empty frame; the
        # tests' rigs mean today's frame by it, said here as `Wiring()`)
        base = r._wiredframe_base = r.wiring if r.wiring is not G.EMPTY else G.Wiring()
    shows = [s.shows if isinstance(s, Thru) else Shows(s.scene, s.hands) for s in states]
    # (plan 36 T4: old words' look-back as the renderer's `dream.on` had it)
    st = getattr(getattr(r, "lookback", None), "state", None)
    look = (M.look_of({"dream.on": bool(st.on), "dream.mix": st.mix}) if st is not None
            else "off")
    r.wiring = wiring(base, *shows, look=look)
    return [Switches(dim=s.dim, flip_x=s.flip_x, flip_y=s.flip_y) for s in states]


def views(shows, size=(10, 10)) -> list[View]:
    """One window per state, every mute on (the state is its wiring)."""
    return [View(Switches(), size) for _ in shows]


def graph(shows, src: Any = None, effects: tuple[str, ...] = (), clouds: tuple[str, ...] = (),
          size=(10, 10), **kw) -> G.Graph:
    """The frame `src` draws on one window per state of `shows`."""
    return G.build_graph(views(shows, size), wiring(src, *shows, **kw), tuple(clouds),
                         tuple(effects))


# ---- the wired frame's round trip, for the tests (row 394) ----
#
# Until row 394 a save below `/6` wrote a wired frame back in plan 33's words
# by its round trip (`graphmigrate.unwired`); no save does now, so the
# production code is gone. Tests written in plan 33's words still read a
# landed frame back that way to compare it, so the round trip lives here.


def has_frame_run(spec) -> bool:
    """Whether a section has a run's head: a wired frame, or a wire from
    `frame` or into `fx.image`."""
    return spec is not None and (spec.wired or any(w.src == "frame" or w.dst == "fx.image"
                                                   for w in spec.all_wires()))


def _old_dst(dst: Any) -> Any:
    """A wire's `to` back in the old ids (`_new_dst`'s inverse)."""
    if not isinstance(dst, str):
        return dst
    got = G.old_id(dst)
    if got != dst:
        return got
    node, dot, port = dst.rpartition(".")
    return f"{G.old_id(node)}{dot}{port}" if dot else dst


def _canonical(section: dict, files: set[str] | None) -> dict | None:
    try:
        # (plan 36 T4: a frame before the split, read as the migration reads one)
        return G.read_graph(section, effects=files, placements=True).to_json()
    except G.GraphError:
        return None


def _unsplit(section: dict) -> dict:
    """Plan 36 T4's look-back split undone, for the round trip below: a
    frame in the words before T4 again (`graphmigrate.split_lookback`
    backwards) — the "add" composite laying the trail (or a dream of it) on
    `X` is `X → lookback.image` and the look-back read in its place, its
    record `lookback.capture`; a frame with no look-back at all (the old
    one off) gets the look-back of today's frame back, over the head of All
    outputs' run (the scene or the backdrop), recording the scene, its
    cover after the faces' pattern."""
    wires = [dict(w) for w in section.get("wires") or [] if isinstance(w, dict)]
    nodes = [dict(n) for n in section.get("nodes") or [] if isinstance(n, dict)]
    into = {w["to"]: w["from"] for w in wires}
    lays = [n for n in nodes if n.get("kind") == "composite" and n.get("blend") == "add"
            and into.get(f"{M._named('composite', int(n.get('instance', 1)))}.over")
            in ("lookback", "dream")]
    out: list[dict] = []
    if lays:
        comp = M._named("composite", int(lays[0].get("instance", 1)))
        under, occ = into.get(f"{comp}.under"), into.get("lookback.occluder")
        nodes = [n for n in nodes if n is not lays[0] and n.get("kind") != "dream"]
        put = False
        for w in wires:
            node = w["to"].rpartition(".")[0]
            if w["to"] in ("lookback.occluder", "dream.image") or node == comp:
                if not put:
                    out.append({"from": under, "to": "lookback.image"})
                    if occ is not None and occ != under:
                        out.append({"from": occ, "to": "lookback.occluder"})
                    put = True
                continue
            if w["to"] == "lookback.image":
                w["to"] = "lookback.capture"
            if w["from"] == comp:
                w["from"] = "lookback"
            out.append(w)
        return {**section, "nodes": nodes, "wires": out}
    if any("lookback" in (w["from"], w["to"].rpartition(".")[0]) for w in wires):
        return section
    head = into.get(f"{G.ALL_OUTPUTS}.image")
    run: list[str] = []
    while M._kind(head) == "effect" and head not in run:
        run.insert(0, head)
        head = into.get(f"{head}.image")
    if head not in ("scene", "backdrop"):
        return section
    first = f"{run[0]}.image" if run else f"{G.ALL_OUTPUTS}.image"
    throughs = {w["to"] for w in wires if w["from"] == head and w["to"].endswith(".under")
                and M._kind(into.get(w["to"].rpartition(".")[0] + ".over")) == "layer"}
    for w in wires:
        if w["from"] == head and (w["to"] == first or w["to"] in throughs):
            if w["to"] == first:
                out.append({"from": head, "to": "lookback.image"})
                if head == "backdrop":
                    out.append({"from": "scene", "to": "lookback.occluder"})
            w["from"] = "lookback"
        out.append(w)
        if w["to"] == f"{G.ALL_OUTPUTS}.guide":
            out.append({"from": "scene", "to": "lookback.capture"})
        if (w["from"], w["to"]) == ("pattern", "shape.faces"):
            out.append({"from": "scene.cover", "to": "lookback.cover"})
    return {**section, "nodes": nodes, "wires": out}


def unwired(section: Any, specs: M.Specs | None = None) -> tuple[dict, bool] | None:
    """A wired frame's round trip (plan 35 M, row 384): (the section in the
    old ids that `migrate` writes as exactly this frame, the
    `backdrop.history` its capture wire says), or None when there is none —
    the frame was edited, or it says what no section before it can (a copy,
    a frame node's entry, a picture into All outputs that is not the run).

    The rest: the section with the marker, the frame's own wires (the
    scene's geometry, `backdrop.scene`, the look-back's picture, occluder
    and capture — the capture's composite with them —, All outputs' and
    every `ground`) taken out; the run behind `output.all.image` written as
    `frame → … → fx.image` again; `into` (a hands node in the scene's
    geometry) and `holds` (a capture of a composite laying the layer on)
    put back as read off those wires; every id put back through `old_id`.
    It is the round trip only when `wired_section` of it is this section
    (both read: the same `to_json`, so node order and the bare entries a
    read drops do not count)."""
    if not isinstance(section, dict) or section.get(G.FRAME_KEY) != G.WIRED_FRAME:
        return None
    files = M._files(specs)
    section = _unsplit(section)              # (plan 36 T4: before the split)
    want = _canonical(section, files)
    if want is None:
        return None
    raw = [w for w in section.get("wires") or [] if isinstance(w, dict)]
    pairs = [(w.get("from"), w.get("to")) for w in raw]
    if any(M._kind(x) == "copy" for a, b in pairs
           for x in (a, b.rpartition(".")[0] if isinstance(b, str) else None)):
        return None
    into = {b: a for a, b in pairs}
    # the run: All outputs' picture back through its effects to the look-back
    run: list[str] = []
    head = into.get(f"{G.ALL_OUTPUTS}.image")
    while M._kind(head) == "effect" and head not in run:
        run.insert(0, head)
        head = into.get(f"{head}.image")
    if head != "lookback":
        return None
    run_pairs = set(zip(["lookback", *run], [f"{e}.image" for e in run]))
    run_pairs.add(((run or ["lookback"])[-1], f"{G.ALL_OUTPUTS}.image"))
    # the capture: the scene or the backdrop, or a composite of one with the
    # layer over (`holds: scene+hands`)
    held = into.get("lookback.capture")
    holds, comp = "scene", None
    if M._kind(held) == "composite" and M._kind(into.get(f"{held}.over")) == "layer":
        holds, comp, held = "scene+hands", held, into.get(f"{held}.under")
    history = held == "backdrop"
    frame_src = {"scene.geometry": None, "backdrop.scene": ("scene",),
                 "lookback.image": ("scene", "backdrop"), "lookback.occluder": ("scene",),
                 "lookback.capture": None}
    wires: list[dict] = []
    for w, (a, b) in zip(raw, pairs):
        node = b.rpartition(".")[0] if isinstance(b, str) else None
        if (a, b) in run_pairs or node == G.ALL_OUTPUTS or a == G.GROUND:
            continue
        # (plan 36 T2: the hidden edges' wires, which `drawn_edges` writes)
        if (a, b) == ("pattern", "shape.faces") or a in G.PINS or (
                isinstance(b, str) and b.endswith(".hands") and M._kind(node) in ("layer",
                                                                               "guide")):
            continue
        if b in frame_src and (frame_src[b] is None or a in frame_src[b]):
            continue
        if comp is not None and (node == comp or a == comp):
            continue
        wires.append({**w, "from": G.old_id(a), "to": _old_dst(b)})
    wires += M._chain("frame", run, "fx.image")
    in_scene = {a for a, b in pairs if b == "scene.geometry" and M._kind(a) == "hands"}
    nodes: list[dict] = []
    seen: set[int] = set()
    for e in section.get("nodes") or []:
        if not isinstance(e, dict):
            continue
        kind = e.get("kind")
        if kind in (*G.FRAME_KINDS, "copy"):
            continue
        if kind == "composite" and comp is not None and M._named(
                "composite", int(e.get("instance", 1))) == comp:
            continue
        e = dict(e)
        if kind == "hands":
            n = int(e.get("instance", 1))
            seen.add(n)
            if G.wired_hands_name(n) in in_scene:
                e["into"] = "scene"
        for key in G.PLACE_KEYS:
            if key in e:
                e[key] = G.old_id(e[key])
        nodes.append(e)
    for name in sorted(in_scene, key=lambda h: G.split_instance(h)[1]):
        n = G.split_instance(name)[1] if name != "hands" else 1
        if n not in seen:
            nodes.append({"kind": "hands", **({"instance": n} if n != 1 else {}),
                          "into": "scene"})
    if holds != "scene":
        nodes.append({"kind": "history", "holds": holds})
    rest = {"nodes": nodes, "wires": wires}
    try:
        old = G.read_graph(rest, effects=files)
    except G.GraphError:
        return None
    # (a placement or wire the read refuses stays as the file had it, refused
    # again either way: the canonical reads below leave it out on both sides)
    again = _canonical(M.wired_section(M.renamed(rest), old, backdrop_history=history), files)
    return (rest, history) if again == want else None
