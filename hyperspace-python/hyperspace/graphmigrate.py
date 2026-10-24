"""Old presets as wires, and wires back as old values (plan 33 M).

Until plan 33 an effect's place in the picture was a number: `fx.<n>.order`
in the stack, `fx.<n>.target` (the frame or the faces), and the faces' and
backdrop's channel were `view.media` / `backdrop.channel`. The free graph
says all of that as wires, so a preset written before it has to be read as
wires (`to_free`, `migrate`), and a graph that `/4` can say has to be
written back as the values a build from before plan 33 reads
(`legacy_values`). A graph `/4` cannot say is `hyperspace.preset/5`
(`needs_free`, row 347): the lowest schema that loses nothing.

Pure data: it reads dicts and `graph.GraphSpec`, touches no params, preset
or media module, and nothing here draws.

Rows 346 and 350 are what it keeps and what it makes:

- Only the effects that are on with mix > 0 join a run (row 346): the owner
  reads the library as using no effect that is switched off, so an off
  effect drew nothing and leaving it out changes no picture. One left out
  while something in the preset drives its params is said in a load note.
- `migrate(doc, specs)` is the whole-document entry point (the section, the
  values with the retired ones dropped, any switch's select, the retargeted
  rows, the notes); `to_free(doc, specs)` is its section and notes alone.
- A route onto `view.media` or `backdrop.channel` becomes a switch over the
  eight channels (row 350), the rows retargeted onto `switch.select`.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from . import graph as G
from .fx import reordered

FREE_SCHEMA = "hyperspace.preset/5"
RETIRED = ("fx.select", "view.media", "backdrop.channel")
CHANNELS = "abcdefgh"
# an effect no spec is to hand for: EffectSpec's own defaults
DEFAULT_ORDER, DEFAULT_MIX = 50, 1.0
Specs = dict[str, tuple[int, float]]   # effect name -> its file's (@order, @mix)

_RETIRED_FX = re.compile(r"fx\..+\.(order|target)")


def retired(pid: str) -> bool:
    """Whether `pid` is a value the free graph retires: `fx.select`,
    `view.media`, `backdrop.channel`, an effect's `order` and `target`."""
    return pid in RETIRED or bool(_RETIRED_FX.fullmatch(pid))


def effect_of(pid: str) -> str | None:
    """The effect instance an `fx.<name>.<key>` id belongs to (`fx.acid.mix`
    → `acid`, `fx.acid.2.mix` → `acid.2`); None for anything else,
    `fx.on` and `fx.mix` included."""
    parts = pid.split(".")
    if parts[0] != "fx" or len(parts) < 3:
        return None
    return ".".join(parts[1:-1])


# ---------------------------------------------------------------- what drives what

def _rows(doc: dict, key: str) -> list[dict]:
    v = doc.get(key)
    return [r for r in v if isinstance(r, dict)] if isinstance(v, list) else []


def _subs(doc: dict):
    macros = doc.get("macros")
    for m in (macros.values() if isinstance(macros, dict) else ()):
        subs = m.get("subs") if isinstance(m, dict) else None
        for sub in (subs if isinstance(subs, list) else ()):
            if isinstance(sub, dict):
                yield sub


def targets(doc: dict) -> frozenset[str]:
    """Every param id a route, desk row or macro subscriber in `doc` drives.
    A modifier's output and a sequencer step drive through a route (their
    lane is the route's source), so the routes carry them."""
    out: set[str] = set()
    for row in (*_rows(doc, "routes"), *_rows(doc, "desk")):
        if isinstance(row.get("target"), str):
            out.add(row["target"])
    for sub in _subs(doc):
        if isinstance(sub.get("base"), str):
            out.add(sub["base"])
        dep = sub.get("depth")
        if isinstance(dep, dict) and isinstance(dep.get("target"), str):
            out.add(dep["target"])
    return frozenset(out)


def _retarget(doc: dict, old: str, new: str) -> None:
    """Every row of `doc` that drives `old` drives `new` (in place)."""
    for row in (*_rows(doc, "routes"), *_rows(doc, "desk")):
        if row.get("target") == old:
            row["target"] = new
    for sub in _subs(doc):
        if sub.get("base") == old:
            sub["base"] = new
        dep = sub.get("depth")
        if isinstance(dep, dict) and dep.get("target") == old:
            dep["target"] = new


# ---------------------------------------------------------------- the section as wires

def _values(doc: dict) -> dict:
    v = doc.get("values")
    return v if isinstance(v, dict) else {}


def _spec_of(specs: Specs | None, name: str) -> tuple[int, float]:
    specs = specs or {}
    return specs.get(name, specs.get(name.partition(".")[0], (DEFAULT_ORDER, DEFAULT_MIX)))


def _mix_of(values: dict, name: str, specs: Specs | None = None) -> float:
    default = float(_spec_of(specs, name)[1])
    try:
        return float(values.get(f"fx.{name}.mix", default))
    except (TypeError, ValueError):
        return default


def _is_on(values: dict, name: str) -> bool:
    return bool(values.get(f"fx.{name}.on", False))


def _file_order(specs: Specs | None, name: str) -> int:
    return int(_spec_of(specs, name)[0])


def _driven_fx(driven: frozenset[str]) -> set[str]:
    return {n for n in (effect_of(p) for p in driven) if n}


def _live(values: dict, specs: Specs | None, driven_fx: set[str], name: str) -> bool:
    """Whether an effect is in a run's membership (row 346, R5): `on`, and
    either mix above 0 or something driving one of its params — an effect
    toggled on at mix 0 and ridden up by a route is used."""
    return _is_on(values, name) and (_mix_of(values, name, specs) > 0 or name in driven_fx)


def _order_of(values: dict, specs: Specs | None, name: str) -> int:
    got = values.get(f"fx.{name}.order")
    return int(got) if isinstance(got, (int, float)) and not isinstance(got, bool) \
        else _file_order(specs, name)


def _candidates(values: dict, specs: Specs | None) -> list[str]:
    """Every effect instance the values or the specs name."""
    names = set(specs or ())
    names.update(n for n in (effect_of(k) for k in values) if n)
    if specs:                       # an effect no file is to hand for is not in this build
        names = {n for n in names if n in specs or n.partition(".")[0] in specs}
    return sorted(names)


def _wired_effects(spec: G.GraphSpec) -> set[str]:
    """The effects the section places or wires (a wire's end, D1's too) —
    but for an `aux` wire, which places neither end (plan 32 R): the effect
    stays in its run."""
    out: set[str] = set()
    for w in spec.all_wires():
        if G.is_aux(w):
            continue
        for name in (w.src, w.node):
            if G.wire_node_kind(name) == "effect":
                out.add(name)
    return out


def _chain(head: str, run: list[str], end: str) -> list[dict]:
    """`head → run[0] → … → run[-1] → end` as wire entries."""
    names = [head, *run]
    wires = [{"from": a, "to": f"{b}.image"} for a, b in zip(names, run)]
    wires.append({"from": names[-1], "to": end})
    return wires


def _next_switch(nodes: list) -> int:
    taken = {int(n.get("instance", 1)) for n in nodes
             if isinstance(n, dict) and n.get("kind") == "switch"}
    return next(i for i in range(1, len(taken) + 2) if i not in taken)


def migrate(doc: dict, specs: Specs) -> tuple[dict, list[str]]:
    """`doc` read as the free graph: (a copy with the graph section holding
    the runs and channel wires, the retired values dropped, any switch's
    `select` set and the rows that drove a channel choice retargeted; the
    load notes). `to_free` is this document's graph section alone.

    Run membership (row 346): aimed at the frame (`target` absent or 0)
    or the faces (1), not placed or wired by the section, and `on` with
    (`mix` > 0, or something drives the effect: R5); in `(order, name)`
    order, the `order` from the document else `specs` (name → the file's
    `(@order, @mix)`; an instance takes its file's, and a value the document
    leaves out takes its file's too). The frame run is always written, bare
    `frame → fx.image` when empty, so a migrated section is recognisable
    (`needs_free`). A
    section that already has a run from `frame` (or `pattern`), or a wire
    into `pattern.media` / `backdrop.image`, is not given another."""
    out = copy.deepcopy(doc)
    notes: list[str] = []
    values = _values(out)
    section = out.get("graph")
    section = section if isinstance(section, dict) else {}
    try:
        spec = G.read_graph(section)
    except G.GraphError:
        spec = None                     # the loader says so and takes the default graph
    if spec is None:
        for pid in [p for p in values if retired(p)]:
            del values[pid]
        return out, notes
    nodes = list(section.get("nodes", []))
    wires = list(section.get("wires", []))
    wired = _wired_effects(spec)
    placed = {e.name for e in spec.effects if e.placed}
    on_wires = spec.all_wires()
    has_frame = any(w.src == "frame" or w.dst == "fx.image" for w in on_wires)
    has_faces = any(w.src == "pattern" or w.dst == "shape.faces" for w in on_wires)
    has_media = any(w.dst == "pattern.media" for w in on_wires)
    has_back = any(w.dst == "backdrop.image" for w in on_wires)
    runs: dict[int, list[str]] = {0: [], 1: []}
    left_out: list[str] = []
    driven = targets(out)
    driven_fx = _driven_fx(driven)
    for name in _candidates(values, specs):
        if name in wired or name in placed:
            continue
        if _live(values, specs, driven_fx, name):
            side = 1 if values.get(f"fx.{name}.target", 0) == 1 else 0
            runs[side].append(name)
        elif name in driven_fx:
            left_out.append(name)
    for run in runs.values():
        run.sort(key=lambda n: (_order_of(values, specs, n), n))
    new_wires: list[dict] = []
    if not has_frame:           # an empty run is the bare `frame → fx.image`: always a head
        new_wires += _chain("frame", runs[0], "fx.image") if runs[0] else [
            {"from": "frame", "to": "fx.image"}]
    if runs[1] and not has_faces:
        new_wires += _chain("pattern", runs[1], "shape.faces")
    declared = {(n.get("file"), int(n.get("instance", 1))) for n in nodes
                if isinstance(n, dict) and n.get("kind") == "effect"}
    for name in [*(runs[0] if not has_frame else ()), *(runs[1] if not has_faces else ())]:
        file, n = G.split_instance(name)
        if n > 1 and (file, n) not in declared:
            nodes.append({"kind": "effect", "file": file, "instance": n})
            declared.add((file, n))
    for name in sorted(left_out):
        notes.append(f"{name} was off, so it is not in the run: wire it in on GRAPH to use it")
    for old, end, has in (("view.media", "pattern.media", has_media),
                          ("backdrop.channel", "backdrop.image", has_back)):
        k = values.get(old, 0)
        k = int(k) if isinstance(k, (int, float)) and not isinstance(k, bool) else 0
        k = k if 0 <= k <= len(CHANNELS) else 0
        if has:
            continue
        if old in driven:
            n = _next_switch(nodes)
            sw = G.SwitchAt(n).name
            nodes.append({"kind": "switch", **({"instance": n} if n != 1 else {})})
            new_wires += [{"from": f"media.{c}", "to": f"{sw}.in{i}"}
                          for i, c in enumerate(CHANNELS, 1)]
            new_wires.append({"from": sw, "to": end})
            select = f"{sw}.select"
            values[select] = k
            _retarget(out, old, select)
        elif k > 0:
            new_wires.append({"from": f"media.{CHANNELS[k - 1]}", "to": end})
    for pid in [p for p in values if retired(p)]:
        del values[pid]
    if new_wires or nodes != list(section.get("nodes", [])):
        sec = {k: v for k, v in section.items() if k not in ("nodes", "wires")}
        sec["nodes"] = nodes
        sec["wires"] = [*wires, *new_wires]
        out["graph"] = sec
    return out, notes


def to_free(doc: dict, specs: Specs) -> tuple[dict, list[str]]:
    """The section half of `migrate`: `doc`'s `graph` section with its runs and channel wires added
    (unchanged when it already has them; `{}` for a preset with no section
    and nothing to add), and the load notes. `migrate` is the rest of the
    document: the values and rows this changes."""
    out, notes = migrate(doc, specs)
    section = out.get("graph")
    return (section if isinstance(section, dict) else {}), notes


# ---------------------------------------------------------------- and back to /4

def uses_free_words(spec: G.GraphSpec) -> bool:
    """Whether a graph says anything beyond plan 26–32's: a new wire end
    (`frame`, `fx.image`, `pattern`, `shape.faces`, `backdrop.image`), a
    switch, a channel into an effect (a branch), or an effect wired and
    reaching nothing."""
    if spec.switches:
        return True
    for w in spec.all_wires():
        if (G.wire_node_kind(w.src) in ("frame", "pattern", "switch")
                or w.dst in ("fx.image", "shape.faces", "backdrop.image")
                or G.wire_node_kind(w.node) in ("pattern", "switch")):
            return True
        if G.wire_node_kind(w.src) == "media" and G.wire_node_kind(w.node) == "effect" \
                and not G.is_aux(w):
            return True
    return bool(_unreached(spec))


def _unreached(spec: G.GraphSpec) -> set[str]:
    """Effects the section wires that reach no sink — but a placed one,
    which the old graph runs where it sits."""
    placed = {e.name for e in spec.wiring().placed}
    return _wired_effects(spec) - G.reaches(spec) - placed


def _expected(head: str, run: tuple[str, ...], end: str) -> set[G.Wire]:
    """The wires that touch `head` or `end` when the run is the only path
    between them: the run's first and last (or the bare `head → end`)."""
    if not run:
        return set()
    return {G.Wire(head, f"{run[0]}.image"), G.Wire(run[-1], end)}


def legacy_values(section: dict, values: dict, specs: Specs | None = None,
                  driven: frozenset[str] = frozenset()) -> dict | None:
    """The `order` / `target` / `view.media` / `backdrop.channel` values
    that say `section` in `/4` terms, or None when `/4` cannot: a branch,
    an unreached effect, more than one run from a head, anything but a
    channel into `pattern.media` / `backdrop.image`, a switch, a run
    member that is off, or an effect that is on outside every run.

    The result is what to lay over `values`: an effect's `order` (kept as it
    is where the run already sorts by `(order, name)`, else
    `fx.reordered`'s fewest changes), its `target`, and the two channel
    choices. A key the document does not hold and that needs no change is
    left out. `specs` gives an absent order or mix its file's default;
    `driven` is `targets(doc)`, so an effect on at mix 0 and driven is a
    member as `migrate` has it (R5)."""
    try:
        spec = G.read_graph(section if isinstance(section, dict) else {})
    except G.GraphError:
        return None
    if spec.switches:
        return None
    wires = spec.all_wires()
    runs = {"frame": G.run_of(spec), "pattern": G.run_of(spec, "pattern", "shape.faces")}
    ends = {"frame": "fx.image", "pattern": "shape.faces"}
    members = {n for r in runs.values() for n in r}
    driven_fx = _driven_fx(driven)
    for head, end in ends.items():
        touching = {w for w in wires if w.src == head or w.dst == end}
        want = _expected(head, runs[head], end)
        if touching != want and not (not runs[head] and touching <= {G.Wire(head, end)}):
            return None
    for name in members:
        if sum(1 for w in wires if w.src == name) != 1:
            return None
        if not _live(values, specs, driven_fx, name):
            return None
    for end in ("pattern.media", "backdrop.image"):
        for w in wires:
            if w.dst == end and G.wire_node_kind(w.src) != "media":
                return None
    wired = _wired_effects(spec)
    if _unreached(spec) - members:
        return None
    placed = {e.name for e in spec.wiring().placed}
    for name in _candidates(values, specs):
        if (name not in members and name not in wired and name not in placed
                and _live(values, specs, driven_fx, name)):
            return None
    out: dict[str, Any] = {}
    for head, run in runs.items():
        if not run:
            continue
        seq = list(run)
        orders = {n: _order_of(values, specs, n) for n in seq}
        new = {**orders, **reordered(seq, orders, seq[-1])}
        for n in seq:
            if f"fx.{n}.order" in values or new[n] != orders[n]:
                out[f"fx.{n}.order"] = new[n] if new[n] != orders[n] else values.get(
                    f"fx.{n}.order", new[n])
            if head == "pattern":
                out[f"fx.{n}.target"] = 1
            elif f"fx.{n}.target" in values:
                out[f"fx.{n}.target"] = 0
    for old, end in (("view.media", "pattern.media"), ("backdrop.channel", "backdrop.image")):
        src = next((w.src for w in wires if w.dst == end), None)
        k = CHANNELS.index(src[-1]) + 1 if src is not None else 0
        if k > 0 or old in values:
            out[old] = k
    return out


def has_frame_run(spec: G.GraphSpec) -> bool:
    """Whether the section has a run's head: a wire from `frame` or into
    `fx.image` (what `to_free` always writes)."""
    return any(w.src == "frame" or w.dst == "fx.image" for w in spec.all_wires())


def needs_free(section: Any, values: dict, driven: frozenset[str] = frozenset()) -> bool:
    """Whether a preset's graph section must be written as `/5` (row 347):
    it has a `frame` run or uses the free graph's words, and `/4` cannot
    say it. A section with neither (plan 26-32's) never is."""
    if not isinstance(section, dict) or not section:
        return False
    try:
        spec = G.read_graph(section)
    except G.GraphError:
        return False
    return ((has_frame_run(spec) or uses_free_words(spec))
            and legacy_values(section, values, None, driven) is None)
