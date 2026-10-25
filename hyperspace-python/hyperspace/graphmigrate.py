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

FREE_SCHEMA = "hyperspace.preset/5"
RETIRED = ("fx.select", "view.media", "backdrop.channel")
CHANNELS = "abcdefgh"
# an effect no spec is to hand for: EffectSpec's own defaults
DEFAULT_ORDER, DEFAULT_MIX = 50, 1.0
Specs = dict[str, tuple[int, float]]   # effect name -> its file's (@order, @mix)

_RETIRED_FX = re.compile(r"fx\..+\.(order|target)")
# the load note for an effect left out of a run while the preset drives it
LEFT_OUT = "{name} was off, so it is not in the run: wire it in on GRAPH to use it"


def left_out_note(name: str) -> str:
    """The load note for effect `name` left out of a run (row 346) while
    something in the preset drives one of its params."""
    return LEFT_OUT.format(name=name)


def left_out_of(note: str) -> str | None:
    """The effect a `left_out_note` names, or None for any other note."""
    head, _, tail = LEFT_OUT.partition("{name}")
    if note.startswith(head) and note.endswith(tail) and len(note) > len(head) + len(tail):
        return note[len(head):len(note) - len(tail)]
    return None


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


# ---------------------------------------------------------------- an old stack's orders

# `fx.<n>.order`'s range on a build from before plan 33 (it clamped there)
MAX_ORDER = 99


def reordered(seq: list[str], orders: dict[str, int], moved: str) -> dict[str, int]:
    """Orders (0…MAX_ORDER) under which sorting by (order, name) gives
    `seq`, changing as few effects as possible: `moved` alone when it can
    be done, else the smallest run of neighbours that can. Returns only
    the effects whose order changes.

    Plan 33 T7: here, not in fx.py, because a stack's order is now only a
    `/4` file's word — `legacy_values` writes a run back as the orders a
    build from before plan 33 sorts into it (it was the FX page's drop,
    plan 20 WP3, until the stack retired). Pure: it reads nothing but its
    arguments.

    One run of `seq` is renumbered: the shortest whose two sides already
    sort as `seq` has them and which has room — as many integers strictly
    between the orders either side of it as it has effects. It gets those
    integers evenly spaced (one effect alone: the middle of its gap). So
    no tie is ever made or relied on, and the name tie-break cannot reorder
    the result; a tie that is already there and not in the way is left
    alone. Of two runs of one length, one holding `moved` is taken, then the
    one further right: the same input always gives the same orders. With no
    room for a short run the run grows, to the whole list at worst (0…99:
    up to a hundred effects; past that orders repeat)."""
    def key(k: int) -> tuple[int, str]:
        return orders[seq[k]], seq[k]
    n = len(seq)
    bad = [k for k in range(1, n) if not key(k - 1) < key(k)]    # seq[k] is out of place
    if not bad:
        return {}                                    # it already sorts that way
    first, last = bad[0], bad[-1]                    # seq[:first] and seq[last:] sort as they are
    i = seq.index(moved)
    for size in range(max(1, last - first), n + 1):
        los = range(min(first, n - size), max(0, last - size) - 1, -1)
        for lo in sorted(los, key=lambda lo: not lo <= i < lo + size):   # stable: right first
            hi = lo + size                           # the run is seq[lo:hi]
            a = orders[seq[lo - 1]] if lo > 0 else -1
            b = orders[seq[hi]] if hi < n else MAX_ORDER + 1
            free = b - a - 1                         # the integers strictly between
            if free < size and size != n:            # no room; the whole list is the last resort
                continue
            if size == 1:
                new = [(a + b) // 2]                 # the middle of the gap
            else:                                    # evenly through the gap, in seq's order
                new = [a + 1 + ((2 * j + 1) * free) // (2 * size) for j in range(size)]
            return {name: o for name, o in zip(seq[lo:hi], new, strict=True)
                    if o != orders[name]}
    return {}                                        # not reached: the whole list always returns


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


def targets(doc: dict, desk: list | None = None) -> frozenset[str]:
    """Every param id a route, desk row or macro subscriber in `doc` drives.
    A modifier's output and a sequencer step drive through a route (their
    lane is the route's source), so the routes carry them. `desk`: rows the
    document's own `desk` stands over — a desk template's, which the load
    expands (`preset.Presets.load_doc`) — counted as its desk rows."""
    out: set[str] = set()
    for row in (*_rows(doc, "routes"), *_rows(doc, "desk"), *_dicts(desk)):
        if isinstance(row.get("target"), str):
            out.add(row["target"])
    for sub in _subs(doc):
        if isinstance(sub.get("base"), str):
            out.add(sub["base"])
        dep = sub.get("depth")
        if isinstance(dep, dict) and isinstance(dep.get("target"), str):
            out.add(dep["target"])
    return frozenset(out)


def _dicts(rows: list | None) -> list[dict]:
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _retarget(doc: dict, old: str, new: str, desk: list | None = None) -> None:
    """Every row of `doc` (and of `desk`, a template's) that drives `old`
    drives `new` (in place)."""
    for row in (*_rows(doc, "routes"), *_rows(doc, "desk"), *_dicts(desk)):
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
    """`doc`'s values, the dict itself (made when it has none, so what is
    written into it stays in the document)."""
    v = doc.get("values")
    if not isinstance(v, dict):
        v = doc["values"] = {}
    return v


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


def _files(specs: Specs | None) -> set[str] | None:
    """The effect files `specs` names (None: any well-formed name), what a
    section is read against as the loader reads it (`read_graph`)."""
    return {n.partition(".")[0] for n in specs} if specs else None


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


def _explicit_placements(spec: G.GraphSpec, nodes: list, wires: list) -> tuple[list, list]:
    """A pre-33 section's (`nodes`, `wires`) with each wire D1 would write
    short (`graph.split_wires`: an effect fed by one wire and wired into
    nothing sits `after` its source; one wired into one output's or the
    history's `image` and fed by none sits `into` it) written as the D1
    entry it stood for — `{"kind": "effect", "file": f, ["instance": n,]
    "after" | "into": where}` — and that wire dropped. The owner,
    2026-10-24: a section with a run shortens no wire (`GraphSpec.wiring`),
    so the run `migrate` adds would otherwise turn an old placement into an
    unreached branch; written out, the old preset draws as it did."""
    own = {e.name for e in spec.effects if e.placed}
    synth = [e for e in spec.wiring().placed if e.name not in own]
    if not synth:
        return nodes, wires
    nodes, wires = list(nodes), list(wires)
    for e in synth:
        key, where = e.where
        entry = {"kind": "effect", "file": e.file, **({"instance": e.n} if e.n != 1 else {})}
        at = next((i for i, n in enumerate(nodes)
                   if isinstance(n, dict) and n.get("kind") == "effect"
                   and n.get("file") == e.file and n.get("instance", 1) == e.n), None)
        if at is None:
            nodes.append({**entry, key: where})
        else:
            nodes[at] = {**nodes[at], key: where}
        short = ({"from": where, "to": f"{e.name}.image"} if key == "after"
                 else {"from": e.name, "to": f"{where}.image"})
        wires = [w for w in wires
                 if not (isinstance(w, dict) and (w.get("from"), w.get("to"))
                         == (short["from"], short["to"]))]
    return nodes, wires


def migrate(doc: dict, specs: Specs, *, desk: list | None = None) -> tuple[dict, list[str]]:
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
    into `pattern.media` / `backdrop.image`, is not given another. A
    section given its frame run first has each wire D1 would write short
    written as that D1 entry (`_explicit_placements`; the owner,
    2026-10-24: a section with a run shortens none).

    The retired values (`retired`) are dropped from the copy: no build from
    plan 33 T7 on declares them, and the wires say all they said. A driven
    channel choice becomes its switch (T5, R19).
    `desk`: a desk template's rows the document's `desk` stands over,
    counted in what drives what and retargeted in place."""
    out = copy.deepcopy(doc)
    notes: list[str] = []
    values = _values(out)
    section = out.get("graph")
    section = section if isinstance(section, dict) else {}
    # (read against the files this build has, as the loader reads it: a
    # placement on an effect not on disk is refused there, and its effect
    # takes the run like any other)
    try:
        spec = G.read_graph(section, effects=_files(specs))
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
    driven = targets(out, desk)
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
    if not has_frame:
        nodes, wires = _explicit_placements(spec, nodes, wires)
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
        notes.append(left_out_note(name))
    for old, end, has in (("view.media", "pattern.media", has_media),
                          ("backdrop.channel", "backdrop.image", has_back)):
        k = values.get(old, 0)
        k = int(k) if isinstance(k, (int, float)) and not isinstance(k, bool) else 0
        k = k if 0 <= k <= len(CHANNELS) else 0
        if has:
            continue
        if old in driven:
            # (row 350, R19: a preset that drives a channel choice loads
            # as a switch and saves as /5, which /4 cannot say)
            n = _next_switch(nodes)
            sw = G.SwitchAt(n).name
            nodes.append({"kind": "switch", **({"instance": n} if n != 1 else {})})
            new_wires += [{"from": f"media.{c}", "to": f"{sw}.in{i}"}
                          for i, c in enumerate(CHANNELS, 1)]
            new_wires.append({"from": sw, "to": end})
            select = f"{sw}.select"
            values[select] = k
            _retarget(out, old, select, desk)
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
    document: the values and rows this changes.

    No production caller (a load takes the whole document, `migrate`):
    kept for tests/test_graph_migrate.py, which reads the migration's
    section on its own, one rule at a time."""
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
    `reordered`'s fewest changes), its `target`, and the two channel
    choices. A key the document does not hold and that needs no change is
    left out. `specs` gives an absent order or mix its file's default;
    `driven` is `targets(doc)`, so an effect on at mix 0 and driven is a
    member as `migrate` has it (R5)."""
    try:
        spec = G.read_graph(section if isinstance(section, dict) else {}, effects=_files(specs))
    except G.GraphError:
        return None
    if spec.switches:
        return None
    driven_fx = _driven_fx(driven)
    # R21: an instance 1 kept on no wire (taken out of the run) and live is
    # unreached, a word `/4` lacks (its stack would run it). R26: one that
    # is not live is nothing to `/4` — `legacy_section` strips the entry a
    # build from before plan 33 refuses, and its stack left the effect out
    if any(e.n == 1 and not e.placed and _live(values, specs, driven_fx, e.name)
           for e in spec.effects):
        return None
    wires = spec.all_wires()
    runs = {"frame": G.run_of(spec), "pattern": G.run_of(spec, "pattern", "shape.faces")}
    ends = {"frame": "fx.image", "pattern": "shape.faces"}
    members = {n for r in runs.values() for n in r}
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


def has_frame_run(spec: G.GraphSpec | None) -> bool:
    """Whether the section has a run's head: a wire from `frame` or into
    `fx.image` (what `migrate` always writes). Every preset loaded on this
    build has one; a section with none (None: no preset loaded, an edit on
    the GRAPH page with nothing loaded) has the empty run (R23). The GRAPH
    page's edits ask this too (`graphview`)."""
    return spec is not None and any(w.src == "frame" or w.dst == "fx.image"
                                    for w in spec.all_wires())


def says_free(section: Any) -> bool:
    """Whether a graph section says anything in the free graph's terms: a
    run's head (`has_frame_run`) or a word `/4` lacks (`uses_free_words`).
    A section this build cannot read says nothing."""
    if not isinstance(section, dict) or not section:
        return False
    try:
        spec = G.read_graph(section)
    except G.GraphError:
        return False
    return has_frame_run(spec) or uses_free_words(spec)


def needs_free(section: Any, values: dict, driven: frozenset[str] = frozenset(),
               specs: Specs | None = None) -> bool:
    """Whether a preset's graph section must be written as `/5` (row 347):
    it has a `frame` run or uses the free graph's words, and `/4` cannot
    say it. A section with neither (plan 26-32's) never is. `specs` gives
    an absent order or mix its file's default (`legacy_values`)."""
    return says_free(section) and legacy_values(section, values, specs, driven) is None


# the wire ends only the free graph has: a wire touching one is plan 33's
_FREE_SRCS = ("frame", "pattern", "switch")
_FREE_DSTS = ("fx", "shape", "pattern", "backdrop", "switch")


def _free_end(w: Any) -> bool:
    """Whether wire entry `w` touches an end only the free graph has."""
    if not isinstance(w, dict):
        return False
    src, dst = w.get("from"), w.get("to")
    node = dst.rpartition(".")[0] if isinstance(dst, str) else None
    return (G.wire_node_kind(src) in _FREE_SRCS or G.wire_node_kind(node) in _FREE_DSTS)


RUN_ENDS = (("frame", "fx.image"), ("pattern", "shape.faces"))


def _run_entries(section: dict, ends=RUN_ENDS) -> set[tuple[str, str]]:
    """The (from, to) of every wire of the section's runs — `frame → … →
    fx.image` and `pattern → … → shape.faces` (or those of `ends`), the
    wires between their effects too — that `legacy_values` says as orders
    and targets."""
    try:
        spec = G.read_graph(section)
    except G.GraphError:
        return set()
    out: set[tuple[str, str]] = set()
    for head, end in ends:
        run = G.run_of(spec, head, end)
        if not run:
            continue
        names = [head, *run]
        out.update((a, f"{b}.image") for a, b in zip(names, run))
        out.add((run[-1], end))
    return out


def _free_node(n: Any) -> bool:
    """A node entry only the free graph has: a switch, or (R21) an effect's
    instance 1 named with no placement — a build from before plan 33
    refuses both."""
    if not isinstance(n, dict):
        return False
    if n.get("kind") == "switch":
        return True
    return (n.get("kind") == "effect" and n.get("instance", 1) == 1
            and not any(k in n for k in G.PLACE_KEYS))


def legacy_section(section: Any) -> dict | None:
    """`section` as a build from before plan 33 reads it (R10): the wires
    of its runs (`_run_entries`: what `legacy_values` says as orders and
    targets), every wire touching a free-graph end (`frame`, `fx.image`,
    `pattern`, `shape.faces`, `backdrop.image`, a switch) and the switch
    nodes and (R21) an unwired instance 1 taken out (`_free_node`). A
    section with none of them is returned as it is, the same object; one
    with nothing left (no node, no wire) is None, no
    section, as the GRAPH page lands an emptied graph. None stays None."""
    if not isinstance(section, dict):
        return section
    wires = section.get("wires")
    nodes = section.get("nodes")
    runs = _run_entries(section) if isinstance(wires, list) else set()

    def free(w: Any) -> bool:
        return _free_end(w) or (isinstance(w, dict) and (w.get("from"), w.get("to")) in runs)

    free_wires = isinstance(wires, list) and any(free(w) for w in wires)
    free_nodes = isinstance(nodes, list) and any(_free_node(n) for n in nodes)
    if not (free_wires or free_nodes):
        return section
    out = copy.deepcopy(section)
    if isinstance(nodes, list):
        out["nodes"] = [n for n in out["nodes"] if not _free_node(n)]
    if isinstance(wires, list):
        out["wires"] = [w for w in out["wires"] if not free(w)]
        if not out["wires"]:
            del out["wires"]
    if not out.get("nodes") and "wires" not in out and set(out) <= {"nodes", "wires"}:
        return None
    return out


# ---------------------------------------------------------------- the retired ids, written back

def held_retired(values: dict) -> dict:
    """The retired values a file holds (`retired`; `fx.select` was never
    saved): what a load keeps beside the wires (`preset.GraphSection.held`)
    so a save below `/5` writes them back where the file had them."""
    return {k: v for k, v in (values or {}).items() if retired(k) and k != "fx.select"}


def landed_retired(values: dict, defaults: dict, specs: Specs | None, *, effects: bool = True,
                   channels: bool = True) -> dict:
    """The retired values a build from before plan 33 T7 held after a load
    of `values` (a file's) over `defaults` (its groups' defaults,
    `Library.defaults`), typed as its registry held them — what its save
    wrote, so ours can (`with_retired`). With `effects`: every effect
    file's order (a float: a continuous param the load set) and target (an
    int: an enum), each the file's, else the default's, else the file's
    `@order` and the frame — every instance the load's graph holds too
    (one added since keeps the int its declaration gave it). With
    `channels`: `view.media` and `backdrop.channel` (ints)."""
    src = {**held_retired(defaults), **held_retired(values)}
    out: dict[str, Any] = {}
    for name in sorted(specs or ()) if effects else ():
        out[f"fx.{name}.order"] = _as(float, src.get(f"fx.{name}.order"),
                                      _file_order(specs, name))
        out[f"fx.{name}.target"] = _as(int, src.get(f"fx.{name}.target"), 0)
    if channels:
        for pid in ("view.media", "backdrop.channel"):
            out[pid] = _as(int, src.get(pid), 0)
    return out


def with_retired(values: dict, held: dict, specs: Specs | None = None) -> dict:
    """`values` (a registry's snapshot, which declares no retired id since
    plan 33 T7) with the retired ids a build from before plan 33 declared,
    each where its registry put it — `fx.<n>.order` and `fx.<n>.target`
    right after `fx.<n>.blend`, `view.media` before `view.media_alpha`,
    `backdrop.channel` before `backdrop.alpha` — so an untouched `/4`
    preset saves byte for byte as that build wrote it (Review Focus 1).

    Each takes `held`'s value (what the load landed, `landed_retired`,
    typed), else what that build's declaration gave it — no load since: the
    file's `@order` as an int (`specs`), target 0 (the frame), channel 0
    (off). `legacy_values` then says the graph over these (a run's orders,
    the channels as wired). A new dict; `values` is not changed."""
    out: dict[str, Any] = {}
    for k, v in values.items():
        if k == "view.media_alpha" and "view.media" not in values:
            out["view.media"] = _as(int, held.get("view.media"), 0)
        if k == "backdrop.alpha" and "backdrop.channel" not in values:
            out["backdrop.channel"] = _as(int, held.get("backdrop.channel"), 0)
        out[k] = v
        name = effect_of(k)
        if name is not None and k == f"fx.{name}.blend":
            order = held.get(f"fx.{name}.order")
            out.setdefault(f"fx.{name}.order", order if _is_number(order)
                           else int(_file_order(specs, name)))
            out.setdefault(f"fx.{name}.target", _as(int, held.get(f"fx.{name}.target"), 0))
    return out


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _as(kind, v: Any, default):
    """`v` as `kind` (float, int), else `default` as `kind` — a held value a
    hand-edited file made a string or a bool is that build's default too."""
    return kind(v) if _is_number(v) else kind(default)


# ---------------------------------------------------------------- a rig's run, as a load lands it

def specs_of(fx: Any) -> Specs:
    """An `FxState`'s effect instances as `Specs` — each one's file
    defaults, `(@order, @mix)`; none for no state."""
    got = getattr(fx, "specs", None) or {}
    return {n: (int(sp.order), float(sp.mix)) for n, sp in got.items()}


def state_values(fx: Any) -> dict:
    """An `FxState`'s settings as preset values (`fx.on`, `fx.mix`, every
    `fx.<n>.<key>`): what a rig that set them by hand hands `wiring_for`."""
    out: dict[str, Any] = {"fx.on": bool(getattr(fx, "on", True)),
                           "fx.mix": float(getattr(fx, "mix", 1.0))}
    for name, v in sorted((getattr(fx, "values", None) or {}).items()):
        out.update({f"fx.{name}.{k}": x for k, x in v.items()})
    return out


def wiring_for(values: dict, specs: Specs | None = None, section: dict | None = None
               ) -> G.Wiring:
    """The wiring a preset's `values` (and its `section`, None for none)
    land as — `migrate`, the path a preset load takes, read back
    (`read_graph`). Plan 33 R23: with the order-built stack gone a rig, a
    tool or a test that switches effects on by hand gets its run here, as
    an old preset with those values would: the effects on, by `order` (the
    file's `@order` where the values name none), a faces-aimed one
    (`target` 1) onto the faces."""
    doc = {"values": dict(values)}
    if section is not None:
        doc["graph"] = section
    out, _ = migrate(doc, specs or {})
    section = out.get("graph")
    spec = G.read_graph(section, effects=_files(specs)) if isinstance(section, dict) else None
    return spec.wiring() if spec is not None else G.Wiring(run=())


def wiring_of(fx: Any) -> G.Wiring:
    """`wiring_for` an `FxState` as it stands (`state_values`, `specs_of`):
    the run its switched-on effects make, by their files' `@order` — the
    one line a rig that sets effects by hand needs (R23)."""
    return wiring_for(state_values(fx), specs_of(fx))


# ---------------------------------------------------------------- an fx module's run

def _entry(w: Any) -> tuple[Any, Any] | None:
    return (w.get("from"), w.get("to")) if isinstance(w, dict) else None


def module_runs(section: Any, values: dict, specs: Specs,
                rows: dict | None = None) -> tuple[dict, list[str]]:
    """`section` with an fx module's runs in place of its own (plan 33
    R12): the module's values (`values`, the fx group as the module landed
    it) read as `migrate` reads a preset's — the main run `frame → … →
    fx.image` always replaced (the bare `frame → fx.image` when the module
    has none), the faces run `pattern → … → shape.faces` replaced only when
    the module has one. Every other wire, branch, composite, switch and
    placement stays, and an effect one of them wires is in no run (one
    `image` input). `rows`: the routes, desk and macros that drive what
    (R5's membership). Returns the section and `migrate`'s notes.

    The faces run kept (the module has none) keeps its effects too: the
    module's main run is read with the faces wires in place, so an effect
    the faces run holds is wired there and left out of the main run, which
    closes over the gap (final review, finding 1) — read without them, the
    effect would sit in both runs, two `image` inputs, and `read_graph`
    would refuse both."""
    base = copy.deepcopy(section) if isinstance(section, dict) else {"nodes": []}
    wires = list(base.get("wires") or [])
    main = _run_entries(base, RUN_ENDS[:1]) | {("frame", "fx.image")}
    faces = _run_entries(base, RUN_ENDS[1:])

    def landed(drop: set) -> tuple[dict, list[str]]:
        stripped = {**base, "wires": [w for w in wires if _entry(w) not in drop]}
        doc = {**(rows or {}), "values": dict(values), "graph": stripped}
        out, notes = migrate(doc, specs)
        sec = out.get("graph") if isinstance(out.get("graph"), dict) else stripped
        return sec, notes

    sec, notes = landed(main | faces)
    if faces and not any(isinstance(w, dict) and w.get("from") == "pattern"
                         for w in sec.get("wires") or []):
        sec, notes = landed(main)                    # the module has none: kept, and its effects
    return sec, notes

