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

Plan 35 M (rows 372, 383–385): then every section is a wired frame in the
owner's names — `migrate` renames it (`renamed`, V2) and writes today's
frame as wires (`wired_section`); `backdrop.history` and the look-back's
`holds` are the capture wire. Below `/6` a wired frame is said by its round
trip (`unwired`): exactly the frame `migrate` writes for the section left,
else `hyperspace.preset/6` (`WIRED_SCHEMA`), where `/5` was.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from . import graph as G
from .outputs import MAX_OUTPUTS

FREE_SCHEMA = "hyperspace.preset/5"
# plan 35 (row 385): `/6` is `/5` with the wired frame in the new ids — what
# a save writes where `/5` was (`needs_free`); nothing writes `/5` again
WIRED_SCHEMA = "hyperspace.preset/6"
# plan 35 M (row 381): `backdrop.history` is the capture wire now
RETIRED = ("fx.select", "view.media", "backdrop.channel", "backdrop.history")
# the retired values a wire says now, not a switch (row 381): a row that
# drives one is dropped, said once (`DRIVEN_RETIRED_NOTE`)
WIRE_RETIRED = ("backdrop.history",)
DRIVEN_RETIRED_NOTE = ("{pid} is a wire now (plan 35): its route is dropped — pick what the "
                       "look-back records on LOOKBACK")
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
    `view.media`, `backdrop.channel`, an effect's `order` and `target` —
    and (plan 35, row 381) `backdrop.history`, the capture wire now."""
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


def _drop_driven(doc: dict, pid: str, desk: list | None = None) -> bool:
    """Every row of `doc` (and of `desk`, a template's, in place) that
    drives `pid` taken out — a route, a desk row, a macro subscriber on it
    (plan 35, row 381: a value a wire says now has nothing to drive).
    Whether any was."""
    dropped = False
    for key in ("routes", "desk"):
        rows = doc.get(key)
        if isinstance(rows, list):
            kept = [r for r in rows if not (isinstance(r, dict) and r.get("target") == pid)]
            if len(kept) != len(rows):
                doc[key], dropped = kept, True
    if isinstance(desk, list):
        kept = [r for r in desk if not (isinstance(r, dict) and r.get("target") == pid)]
        if len(kept) != len(desk):
            desk[:], dropped = kept, True
    macros = doc.get("macros")
    for m in (macros.values() if isinstance(macros, dict) else ()):
        subs = m.get("subs") if isinstance(m, dict) else None
        if not isinstance(subs, list):
            continue
        kept = [s for s in subs if not (isinstance(s, dict) and (
            s.get("base") == pid or (isinstance(s.get("depth"), dict)
                                     and s["depth"].get("target") == pid)))]
        if len(kept) != len(subs):
            m["subs"], dropped = kept, True
    return dropped


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


def _members(values: dict, specs: Specs | None, driven: frozenset[str],
             taken: set[str]) -> tuple[dict[int, list[str]], list[str]]:
    """The runs' membership (row 346, R5): ({0: the frame's run, 1: the
    faces'}, each in `(order, name)` order; the effects left out though
    driven) — every effect instance not `taken` (wired or placed by the
    section) that is live, on the side its `target` says."""
    runs: dict[int, list[str]] = {0: [], 1: []}
    left_out: list[str] = []
    driven_fx = _driven_fx(driven)
    for name in _candidates(values, specs):
        if name in taken:
            continue
        if _live(values, specs, driven_fx, name):
            side = 1 if values.get(f"fx.{name}.target", 0) == 1 else 0
            runs[side].append(name)
        elif name in driven_fx:
            left_out.append(name)
    for run in runs.values():
        run.sort(key=lambda n: (_order_of(values, specs, n), n))
    return runs, left_out


def migrate(doc: dict, specs: Specs, *, desk: list | None = None,
            wire: bool = True) -> tuple[dict, list[str]]:
    """`doc` read as the free graph: (a copy with the graph section holding
    the runs and channel wires, the retired values dropped, any switch's
    `select` set and the rows that drove a channel choice retargeted; the
    load notes). `to_free` is this document's graph section alone.

    Plan 35 M (rows 372, 383): then, with `wire` (every load), the section
    in the new ids (`renamed`) written as a wired frame (`wired_section`:
    today's frame for the default switches into All outputs, the capture
    wire saying `backdrop.history` and the look-back's `holds`) — every
    readable section comes out `"frame": "wired"`, an empty one (or none)
    the default frame. A section already wired is the preset's own and is
    kept as it is; an unreadable one is left as it is (the loader says so).
    A row that drives `backdrop.history` is dropped with a note
    (`DRIVEN_RETIRED_NOTE`): the capture is a wire, nothing to drive.
    Without `wire` the section stays as plan 33 wrote it (`to_free`, and
    `wiring_for`'s rigs, which build the default graph from switches until
    T4 retires them).

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
    # plan 35 (row 381): the capture is a wire now — what a row on
    # `backdrop.history` drove has nothing to drive; and the value itself
    # is read once, below, into the capture wire
    for pid in WIRE_RETIRED:
        if _drop_driven(out, pid, desk):
            notes.append(DRIVEN_RETIRED_NOTE.format(pid=pid))
    held_backdrop = bool(values.get("backdrop.history", False))
    section = out.get("graph")
    section = section if isinstance(section, dict) else {}
    # (read against the files this build has, as the loader reads it: a
    # placement on an effect not on disk is refused there, and its effect
    # takes the run like any other)
    try:
        spec = G.read_graph(section, effects=_files(specs))
    except G.GraphError:
        spec = None                     # the loader says so and takes the default graph
    if spec is None or spec.wired:
        # (plan 35: a wired frame is the preset's own words — nothing of
        # plan 33's to add, nothing to rename)
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
    driven = targets(out, desk)
    runs, left_out = _members(values, specs, driven, wired | placed)
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
    if wire:
        # plan 35 M: in the new ids, as a wired frame — `wired_section` reads
        # the frame off the section as plan 33 left it (old ids)
        sec = out.get("graph") if isinstance(out.get("graph"), dict) else {}
        try:
            old = G.read_graph(sec, effects=_files(specs))
        except G.GraphError:
            return out, notes           # (not reached: plan 33's steps write what reads)
        out["graph"] = wired_section(renamed(sec), old, backdrop_history=held_backdrop)
    return out, notes


def to_free(doc: dict, specs: Specs) -> tuple[dict, list[str]]:
    """The section half of `migrate`: `doc`'s `graph` section with its runs and channel wires added
    (unchanged when it already has them; `{}` for a preset with no section
    and nothing to add), and the load notes. `migrate` is the rest of the
    document: the values and rows this changes.

    No production caller (a load takes the whole document, `migrate`):
    kept for tests/test_graph_migrate.py, which reads the migration's
    section on its own, one rule at a time — plan 33's rules, so the
    section as plan 33 wrote it (no wired frame: `migrate`'s `wire`)."""
    out, notes = migrate(doc, specs, wire=False)
    section = out.get("graph")
    return (section if isinstance(section, dict) else {}), notes


# ---------------------------------------------------------------- and back to /4

def uses_free_words(spec: G.GraphSpec) -> bool:
    """Whether a graph says anything beyond plan 26–32's: a new wire end
    (`frame`, `fx.image`, `pattern`, `shape.faces`, `backdrop.image`), a
    switch, a channel into an effect (a branch), or an effect wired and
    reaching nothing. Plan 34 L: or feedback's words — a delay, a resize,
    a look-back frame or the dream, declared or on a wire (`/5` only).
    Plan 35 F: or a wired frame, or a copy (`/6` only)."""
    if spec.wired or spec.copies:
        return True
    if spec.switches or _feedback(spec):
        return True
    for w in spec.all_wires():
        if (G.wire_node_kind(w.src) in ("frame", "pattern", "switch", *FEEDBACK)
                or w.dst in ("fx.image", "shape.faces", "backdrop.image")
                or G.wire_node_kind(w.node) in ("pattern", "switch", *FEEDBACK)):
            return True
        if G.wire_node_kind(w.src) == "media" and G.wire_node_kind(w.node) == "effect" \
                and not G.is_aux(w):
            return True
    return bool(_unreached(spec))


# plan 34 L: the node kinds feedback adds — none has a word in `/4`
FEEDBACK = ("delay", "resize", "echo", "dream")


def _feedback(spec: G.GraphSpec) -> bool:
    """Whether the section declares a delay, a resize, an echo or the dream."""
    return bool(spec.delays or spec.resizes or spec.echoes or spec.dream)


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
    member as `migrate` has it (R5).

    Plan 35 M (row 384): a wired frame is said by its round trip
    (`unwired`): None when it is not exactly the frame `migrate` writes for
    the section left, else that section's values — and `backdrop.history`,
    which the capture wire says, where there is a backdrop to say it of."""
    if isinstance(section, dict) and section.get(G.FRAME_KEY) == G.WIRED_FRAME:
        got = unwired(section, specs)
        if got is None:
            return None
        rest, history = got
        out = legacy_values(rest, values, specs, driven)
        backdrop = any(isinstance(w, dict) and w.get("to") == "backdrop.image"
                       for w in rest.get("wires", []))
        if out is not None and backdrop and (history or "backdrop.history" in values):
            out["backdrop.history"] = history
        return out
    try:
        spec = G.read_graph(section if isinstance(section, dict) else {}, effects=_files(specs))
    except G.GraphError:
        return None
    if spec.switches or _feedback(spec):         # (plan 34 L: no `/4` word for either)
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
    page's edits ask this too (`graphview`). Plan 35: a wired frame is
    one too — every load's section is, its frame its wires."""
    return spec is not None and (spec.wired or any(w.src == "frame" or w.dst == "fx.image"
                                                   for w in spec.all_wires()))


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
    """Whether a preset's graph section must be written as `/6` (row 347,
    plan 35 row 385: `/5` before): it has a `frame` run, is a wired frame
    or uses the free graph's words, and `/4` cannot say it. A section with
    none of them (plan 26-32's) never is. `specs` gives an absent order or
    mix its file's default (`legacy_values`)."""
    return says_free(section) and legacy_values(section, values, specs, driven) is None


# the wire ends only the free graph has: a wire touching one is plan 33's.
# Plan 35 F: and the wired frame's — a copy, `ground`, the shape as a
# source, the scene's geometry — and the ports only a wired frame has
_FREE_SRCS = ("frame", "pattern", "switch", "delay", "resize", "echo", "dream",
              "copy", "ground", "shape")
_FREE_DSTS = ("fx", "shape", "pattern", "backdrop", "switch", "delay", "resize",
              "copy", "scene")
_FREE_PORTS = ("lookback.capture", "lookback.occluder", "backdrop.scene", "output.all.image",
               "output.all.hands", "output.all.guide")


def _free_end(w: Any) -> bool:
    """Whether wire entry `w` touches an end only the free graph has (its
    names read in either frame's kinds: plan 35's copy and ground are a
    wired frame's)."""
    if not isinstance(w, dict):
        return False
    src, dst = w.get("from"), w.get("to")
    node = dst.rpartition(".")[0] if isinstance(dst, str) else None
    return (dst in _FREE_PORTS
            or any(G.wire_node_kind(src, wired=x) in _FREE_SRCS
                   or G.wire_node_kind(node, wired=x) in _FREE_DSTS for x in (False, True)))


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
    refuses both; (plan 34 L) a delay, a resize, an echo or the dream;
    (plan 35 F) a copy or a frame kind's entry (`G.FRAME_KINDS`)."""
    if not isinstance(n, dict):
        return False
    if n.get("kind") in ("switch", *FEEDBACK, "copy", *G.FRAME_KINDS):
        return True
    return (n.get("kind") == "effect" and n.get("instance", 1) == 1
            and not any(k in n for k in G.PLACE_KEYS))


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
        return G.read_graph(section, effects=files).to_json()
    except G.GraphError:
        return None


def unwired(section: Any, specs: Specs | None = None) -> tuple[dict, bool] | None:
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
    files = _files(specs)
    want = _canonical(section, files)
    if want is None:
        return None
    raw = [w for w in section.get("wires") or [] if isinstance(w, dict)]
    pairs = [(w.get("from"), w.get("to")) for w in raw]
    if any(_kind(x) == "copy" for a, b in pairs
           for x in (a, b.rpartition(".")[0] if isinstance(b, str) else None)):
        return None
    into = {b: a for a, b in pairs}
    # the run: All outputs' picture back through its effects to the look-back
    run: list[str] = []
    head = into.get(f"{G.ALL_OUTPUTS}.image")
    while _kind(head) == "effect" and head not in run:
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
    if _kind(held) == "composite" and _kind(into.get(f"{held}.over")) == "layer":
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
        if b in frame_src and (frame_src[b] is None or a in frame_src[b]):
            continue
        if comp is not None and (node == comp or a == comp):
            continue
        wires.append({**w, "from": G.old_id(a), "to": _old_dst(b)})
    wires += _chain("frame", run, "fx.image")
    in_scene = {a for a, b in pairs if b == "scene.geometry" and _kind(a) == "hands"}
    nodes: list[dict] = []
    seen: set[int] = set()
    for e in section.get("nodes") or []:
        if not isinstance(e, dict):
            continue
        kind = e.get("kind")
        if kind in (*G.FRAME_KINDS, "copy"):
            continue
        if kind == "composite" and comp is not None and _named(
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
    again = _canonical(wired_section(renamed(rest), old, backdrop_history=history), files)
    return (rest, history) if again == want else None


def legacy_section(section: Any) -> dict | None:
    """`section` as a build from before plan 33 reads it (R10): the wires
    of its runs (`_run_entries`: what `legacy_values` says as orders and
    targets), every wire touching a free-graph end (`frame`, `fx.image`,
    `pattern`, `shape.faces`, `backdrop.image`, a switch; plan 34's delay,
    resize, echo and dream) and those nodes and (R21) an unwired instance 1
    taken out (`_free_node`). A
    section with none of them is returned as it is, the same object; one
    with nothing left (no node, no wire) is None, no
    section, as the GRAPH page lands an emptied graph. None stays None.

    Plan 35 M (row 384): a wired frame is put back by its round trip
    (`unwired`) and then as above; one with none — an edited frame, a word
    only `/6` has — is returned as it is (`legacy_values` reads it as
    needing `/6`)."""
    if isinstance(section, dict) and section.get(G.FRAME_KEY) == G.WIRED_FRAME:
        got = unwired(section)
        return section if got is None else legacy_section(got[0])
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
    so a save below `/5` (the free graph's words, `/5` and `/6`) writes them
    back where the file had them."""
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
    `channels`: `view.media` and `backdrop.channel` (ints), and (plan 35,
    row 381) `backdrop.history` (a bool: a toggle)."""
    src = {**held_retired(defaults), **held_retired(values)}
    out: dict[str, Any] = {}
    for name in sorted(specs or ()) if effects else ():
        out[f"fx.{name}.order"] = _as(float, src.get(f"fx.{name}.order"),
                                      _file_order(specs, name))
        out[f"fx.{name}.target"] = _as(int, src.get(f"fx.{name}.target"), 0)
    if channels:
        for pid in ("view.media", "backdrop.channel"):
            out[pid] = _as(int, src.get(pid), 0)
        out["backdrop.history"] = bool(src.get("backdrop.history", False))
    return out


def with_retired(values: dict, held: dict, specs: Specs | None = None) -> dict:
    """`values` (a registry's snapshot, which declares no retired id since
    plan 33 T7) with the retired ids a build from before plan 33 declared,
    each where its registry put it — `fx.<n>.order` and `fx.<n>.target`
    right after `fx.<n>.blend`, `view.media` before `view.media_alpha`,
    `backdrop.channel` before `backdrop.alpha` and (plan 35) `backdrop.
    history` after it — so an untouched `/4` preset saves byte for byte as
    that build wrote it (Review Focus 1).

    Each takes `held`'s value (what the load landed, `landed_retired`,
    typed), else what that build's declaration gave it — no load since: the
    file's `@order` as an int (`specs`), target 0 (the frame), channel 0
    (off), the backdrop out of the look-back. `legacy_values` then says
    the graph over these (a run's orders, the channels as wired, the
    capture). A new dict; `values` is not changed."""
    out: dict[str, Any] = {}
    for k, v in values.items():
        if k == "view.media_alpha" and "view.media" not in values:
            out["view.media"] = _as(int, held.get("view.media"), 0)
        if k == "backdrop.alpha" and "backdrop.channel" not in values:
            out["backdrop.channel"] = _as(int, held.get("backdrop.channel"), 0)
        out[k] = v
        if k == "backdrop.alpha" and "backdrop.history" not in values:
            out["backdrop.history"] = held.get("backdrop.history") is True
        name = effect_of(k)
        if name is not None and k == f"fx.{name}.blend":
            order = held.get(f"fx.{name}.order")
            out.setdefault(f"fx.{name}.order", order if _is_number(order)
                           else int(_file_order(specs, name)))
            out.setdefault(f"fx.{name}.target", _as(int, held.get(f"fx.{name}.target"), 0))
    return out


def with_history(values: dict, history: bool) -> dict:
    """`values` with `backdrop.history` (a plan 33/34 build's param, the
    capture wire's now) where that build's registry wrote it, right after
    `backdrop.alpha` (ruling R10: a `/5` save). A new dict."""
    out: dict[str, Any] = {}
    for k, v in values.items():
        if k != "backdrop.history":
            out[k] = v
        if k == "backdrop.alpha":
            out["backdrop.history"] = bool(history)
    if "backdrop.history" not in out:
        out["backdrop.history"] = bool(history)
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
    (`target` 1) onto the faces.

    Plan 35 T3: the section as plan 33 writes it (`migrate`'s `wire` off) —
    the wiring the default graph builds from the outputs' switches, which
    these rigs still set by hand until T4 retires them."""
    doc = {"values": dict(values)}
    if section is not None:
        doc["graph"] = section
    out, _ = migrate(doc, specs or {}, wire=False)
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
    would refuse both.

    Plan 35 M: a wired frame's main run is the chain of effects behind
    `output.all.image` (from its head, the look-back); the module's run
    takes its place where it stands (`_wired_module_runs`)."""
    if isinstance(section, dict) and section.get(G.FRAME_KEY) == G.WIRED_FRAME:
        return _wired_module_runs(section, values, specs, rows)
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


def _chain_into(pairs: list[tuple[Any, Any]], end: str) -> tuple[Any, list[str]]:
    """(the head, the effects first first) of the chain of effects whose
    last goes into `end`, read off `pairs` (from, to)."""
    into = {b: a for a, b in pairs}
    run: list[str] = []
    head = into.get(end)
    while _kind(head) == "effect" and head not in run:
        run.insert(0, head)
        head = into.get(f"{head}.image")
    return head, run


def _wired_module_runs(section: dict, values: dict, specs: Specs,
                       rows: dict | None = None) -> tuple[dict, list[str]]:
    """`module_runs` for a wired frame (plan 35 M): the main run — the
    effects behind `output.all.image`, from its head (the look-back) — is
    the module's, its wires written where the old ones stood (the frame's
    canonical place, so an untouched frame stays `/4`-sayable); the faces'
    run `pattern → … → shape.faces` is the module's only when it has one.
    Every other wire and entry stays; an effect one of them wires is in no
    run. With no picture into All outputs there is no main run to replace."""
    out = copy.deepcopy(section)
    wires = [w for w in out.get("wires") or [] if isinstance(w, dict)]
    pairs = [(w.get("from"), w.get("to")) for w in wires]
    spots = {}
    for side, end in enumerate((f"{G.ALL_OUTPUTS}.image", "shape.faces")):
        head, run = _chain_into(pairs, end)
        if side == 1 and head != "pattern":
            head, run = "pattern", []             # (no faces run: none to replace)
        if head is None:
            continue                              # (nothing into All outputs)
        mine = set(zip([head, *run], [f"{e}.image" for e in run]))
        if run or side == 0:
            mine.add(((run or [head])[-1], end))
        spots[side] = (head, end, mine)

    def members(sides) -> tuple[dict[int, list[str]], list[str]]:
        drop = {p for s in sides if s in spots for p in spots[s][2]}
        left = [w for w in wires if (w.get("from"), w.get("to")) not in drop]
        spec = G.read_graph({**out, "wires": left}, effects=_files(specs))
        taken = _wired_effects(spec) | {e.name for e in spec.effects if e.placed}
        taken |= {c.of for c in spec.copies}
        return _members(values, specs, targets(rows or {}), taken)

    try:
        runs, left_out = members((0, 1))
        if not runs[1] and spots.get(1, (0, 0, ()))[2]:
            # the module has no faces run: the preset's stays, and its
            # effects with it (out of the main run, as `module_runs` keeps them)
            runs, left_out = members((0,))
    except G.GraphError:
        return section, []
    new = list(wires)
    for side, (head, end, mine) in sorted(spots.items(), reverse=True):
        if side == 1 and not runs[1]:
            continue                    # (the module has no faces run: the preset's stays)
        # where the old run stood — the frame's canonical place; a faces run
        # new to the section goes first, with the section's own wires
        at = next((k for k, w in enumerate(new) if (w.get("from"), w.get("to")) in mine),
                  0 if side == 1 else len(new))
        new = [w for w in new if (w.get("from"), w.get("to")) not in mine]
        new[at:at] = _chain(head, runs[side], end)
    declared = {(n.get("file"), int(n.get("instance", 1))) for n in out.get("nodes") or []
                if isinstance(n, dict) and n.get("kind") == "effect"}
    nodes = list(out.get("nodes") or [])
    for name in [*runs[0], *runs[1]]:
        file, n = G.split_instance(name)
        if n > 1 and (file, n) not in declared:
            nodes.append({"kind": "effect", "file": file, "instance": n})
            declared.add((file, n))
    out["nodes"], out["wires"] = nodes, new
    return out, [left_out_note(n) for n in sorted(left_out)]


# ---------------------------------------------------------------- the frame as wires (plan 35 M)
#
# Plan 35 (rows 372, 375, 383): the frame `default_graph` builds from the
# outputs' switches is written as ordinary wires. `frame_wires` is the frame
# for the default switches, written once into All outputs (`output.all`);
# `output_wires` is what one output's state (`Shows`: the switches as the
# migration's own word) adds over that; `wired_section` is a section with
# its frame written. Pure data, as the rest of this module: the canonical
# order (the build plan's nine groups) is what T3's round trip compares.

@dataclass(frozen=True)
class Shows:
    """One output's switch state as the migration reads it (plan 35 M):
    the scene, the hands, the hands through the effects. A word of the
    migration, not of `outputs` (T4 retires `Switches.through`)."""

    scene: bool = True
    hands: bool = True
    through: bool = False


def _w(src: str, dst: str) -> dict:
    return {"from": src, "to": dst}


def _layer_of(n: int) -> str:
    """The n-th hands node's layer in the new ids: `hands.layer`, `hands.2.layer`."""
    return f"{G.wired_hands_name(n)}.layer"


def _guide_of(n: int) -> str:
    """The n-th hands node's guide in the new ids: `hands.guide`, `hands.2.guide`."""
    return f"{G.wired_hands_name(n)}.guide"


def _named(kind: str, n: int) -> str:
    return kind if n == 1 else f"{kind}.{n}"


def _held(spec: G.GraphSpec, kind: str) -> set[int]:
    """The instances of `kind` (`composite`, `copy`) `spec` holds: by an
    entry or by a wire's end."""
    got = {o.n for k, o in spec.others if k == kind}
    for name in (x for w in spec.wires for x in (w.src, w.node)):
        head, _, n = name.partition(".")
        if head == kind and (not n or n.isdigit()):
            got.add(int(n) if n else 1)
    return got


def _next_composite(spec: G.GraphSpec) -> int:
    """The lowest composite instance no entry or wire of `spec` holds: the
    frame's composites are numbered so, the same every time (the round
    trip's canonical choice)."""
    held = _held(spec, "composite")
    return next(k for k in range(1, len(held) + 2) if k not in held)


def _next_copies(spec: G.GraphSpec, count: int) -> list[int]:
    """`count` copy instances no entry or wire of `spec` holds, lowest first."""
    held, out, k = _held(spec, "copy"), [], 1
    while len(out) < count:
        if k not in held:
            out.append(k)
        k += 1
    return out


def frame_wires(spec: G.GraphSpec, *, backdrop_history: bool = False
                ) -> tuple[list[dict], list[dict]]:
    """The frame `default_graph` builds for `spec` under the default
    switches (`Shows()`: the scene, the hands over, not through), as
    (entries, wires) in the new ids, written to All outputs (plan 35 M,
    rows 375 and 383). `spec` is a section as read before the wired frame
    (its `wiring()`: the run, where the hands are, the backdrop, what the
    look-back holds). Its own wires are not in the result — but for its
    run `frame → … → fx.image`, which is written here as `lookback → … →
    output.all.image`.

    The canonical order, one group after another: the scene's geometry
    (the in-scene hands by instance, then the shape), `backdrop.scene`,
    `lookback.image`, `lookback.occluder`, the run, `output.all.image`,
    `.hands`, `.guide`, then the capture (its composite first, for `holds:
    scene+hands`). `backdrop_history` is the preset's `backdrop.history`
    value, which the capture wire says now (T3 retires the param)."""
    wiring = spec.wiring()
    inside = wiring.in_scene()
    layer = _layer_of(wiring.layer_node().n)
    backdrop = bool(wiring.backdrop) or any(w.dst == "backdrop.image" for w in wiring.wires)
    own_image = any(w.dst == "history.image" for w in spec.wires)
    wires = [_w(G.wired_hands_name(h.n), "scene.geometry") for h in inside]
    wires.append(_w("shape", "scene.geometry"))
    if backdrop:
        wires.append(_w("scene", "backdrop.scene"))
    if not own_image:
        wires.append(_w("backdrop" if backdrop else "scene", "lookback.image"))
    if backdrop and not backdrop_history:
        # (plan 32 B-I1: over a backdrop the look-back keeps out of, the
        # scene alone holds the wake back)
        wires.append(_w("scene", "lookback.occluder"))
    run = list(wiring.run or ())
    chain = ["lookback", *run]
    wires += [_w(a, f"{b}.image") for a, b in zip(chain, run)]
    wires.append(_w(chain[-1], "output.all.image"))
    if not inside:
        wires += [_w(layer, "output.all.hands"), _w(layer, "output.all.guide")]
    else:
        # the guide of an output that shows the hands inside its scene: the
        # first in-scene node's (its layer itself while that is built:
        # `build_graph`, as `default_graph`'s `scene_readout`)
        wires.append(_w(_guide_of(inside[0].n), "output.all.guide"))
    entries: list[dict] = []
    held = "backdrop" if backdrop and backdrop_history else "scene"
    if wiring.history == "scene+hands" and not inside:
        k = _next_composite(spec)
        comp = _named("composite", k)
        entries.append(G.CompositeAt(k, wiring.blend).to_json())
        wires += [_w(held, f"{comp}.under"), _w(layer, f"{comp}.over"),
                  _w(comp, "lookback.capture")]
    else:
        wires.append(_w(held, "lookback.capture"))
    return entries, wires


def _new_dst(dst: Any) -> Any:
    """A wire's `to` in the new ids: the whole name (`output.2.readout` →
    `output.2.guide`), else its node's (`history.image` → `lookback.image`)."""
    if not isinstance(dst, str):
        return dst
    got = G.new_id(dst)
    if got != dst:
        return got
    node, dot, port = dst.rpartition(".")
    return f"{G.new_id(node)}{dot}{port}" if dot else dst


def renamed(section: Any) -> Any:
    """A `/2`–`/5` section in the new ids (plan 35 V2, row 373): every wire
    end and D1's `after` / `into` through `graph.new_id`, the port
    `output.<n>.readout` as `output.<n>.guide`, the entry kind `history`
    as `lookback`. A section already wired, or none, is returned as it is.
    (T3 runs it inside `migrate`; T2's builder proof reads through it.)"""
    if not isinstance(section, dict) or section.get(G.FRAME_KEY) == G.WIRED_FRAME:
        return section
    out = copy.deepcopy(section)
    for e in out.get("nodes") or []:
        if not isinstance(e, dict):
            continue
        if e.get("kind") == "history":
            e["kind"] = "lookback"
        for key in G.PLACE_KEYS:
            if key in e:
                e[key] = G.new_id(e[key])
    for w in out.get("wires") or []:
        if isinstance(w, dict):
            if "from" in w:
                w["from"] = G.new_id(w["from"])
            if "to" in w:
                w["to"] = _new_dst(w["to"])
    return out


def with_output_wires(section: dict, n: int, shows: Shows) -> dict:
    """A wired `section` with output `n`'s overrides for `shows`
    (`output_wires`) in place of its own wires into `output.<n>`: the
    entries joining the nodes, the wires the wires. A wire into the output
    the read refuses is kept after them as it stands (plan 35 T3: refused
    again at the load, it is said again, as plan 28 N4 says every refused
    wire)."""
    spec = G.read_graph(section)
    got = output_wires(spec, n, shows)
    port = f"output.{n}."
    stood = {(w.src, w.dst) for w in spec.wires}
    mine = [w for w in section.get("wires", [])
            if isinstance(w, dict) and str(w.get("to", "")).startswith(port)]
    refused = [w for w in mine if (w.get("from"), w.get("to")) not in stood]
    if sorted(map(str, (w for w in mine if w not in refused))) == sorted(map(str, got)):
        return section                     # (its own wires say it already: kept where they are)
    out = dict(section)
    out["nodes"] = [*section.get("nodes", []), *(e for e in got if "kind" in e)]
    out["wires"] = [*(w for w in section.get("wires", [])
                      if not (isinstance(w, dict) and str(w.get("to", "")).startswith(port))),
                    *(w for w in got if "kind" not in w), *refused]
    return out


def wired_section(section: dict, spec: G.GraphSpec, *, backdrop_history: bool = False) -> dict:
    """`section` (in the new ids already: `renamed`) as a wired frame (plan
    35 M): `"frame": "wired"` first; the hands entries without `into` and
    no look-back entry (where the hands are and what the look-back holds
    are wires now); the run's wires dropped and every other wire kept as
    it stands (a stray `frame → x` read as `lookback → x`, `y → fx.image`
    as `y → output.all.image`); then the frame's entries and wires
    (`frame_wires` of `spec`, the section as read before it was renamed)
    appended in the canonical order. The section's own wires into an
    output stay as overrides of All outputs, with `_Wiring._put`'s rules
    applied under the default switches (`with_output_wires(…, Shows())`:
    a picture by a wire drops the guide where the hands were in the scene)."""
    entries, frame = frame_wires(spec, backdrop_history=backdrop_history)
    run = spec.wiring().run
    drop = {(w.src, w.dst) for w in G._run_wires(tuple(run))} if run is not None else set()
    nodes = []
    for e in section.get("nodes") or []:
        if isinstance(e, dict) and e.get("kind") == "hands":
            e = {k: v for k, v in e.items() if k != "into"}
        elif isinstance(e, dict) and e.get("kind") in ("lookback", "history"):
            continue
        nodes.append(e)
    own = []
    for w in section.get("wires") or []:
        if isinstance(w, dict):
            if (w.get("from"), w.get("to")) in drop:
                continue
            w = {**w, **({"from": "lookback"} if w.get("from") == "frame" else {}),
                 **({"to": "output.all.image"} if w.get("to") == "fx.image" else {})}
        own.append(w)
    out = {G.FRAME_KEY: G.WIRED_FRAME, "nodes": [*nodes, *entries], "wires": [*own, *frame]}
    outs = sorted({int(m.group(1)) for w in own if isinstance(w, dict)
                   for m in [re.fullmatch(r"output\.([1-9][0-9]*)\.[a-z]+", str(w.get("to")))]
                   if m is not None and int(m.group(1)) <= MAX_OUTPUTS})
    for n in outs:
        out = with_output_wires(out, n, Shows())
    return out


def _src_into(wires, dst: str) -> str | None:
    return next((w.src for w in wires if w.dst == dst), None)


def _kind(name: str | None) -> str | None:
    return G.wire_node_kind(name, wired=True) if name is not None else None


def output_wires(spec: G.GraphSpec, n: int, shows: Shows) -> list[dict]:
    """Output `n`'s overrides of All outputs under `shows` (plan 35 M):
    exactly the picture, hands and guide `default_graph` gives output `n`
    for that switch state, with `_Wiring._put`'s output rules applied to
    the section's own wires into `output.<n>` (a picture by a wire drops
    the guide where no hands are laid over; a hands wire on a through
    output takes its picture back to the scene's). `spec` is a wired frame
    (`wired_section`). A port that must show nothing though All outputs'
    has something is `ground → output.<n>.<port>`; a port showing what All
    outputs' shows has no wire, so `Shows()` with no wire of the section
    into the output gives `[]`.

    "Through" (the hands on and through, with the scene on and the hands
    not in it, or the scene off) always writes a `composite.k` (the lowest
    free instance, its blend the hands' `laid`; the head of All outputs'
    picture under — the look-back — and nothing under with the scene off;
    the layer over) and one `copy` of each effect of All outputs' run
    (none for an empty run), `composite.k → copy → … → output.<n>.image`,
    each copy with its original's aux wire; whether it bends is the
    frame's (`Shown.bent`). Entries come first in the list (the dicts with
    `kind`), then the wires. The section's own `ground` wires into the
    output are not read: they are what an earlier call wrote."""
    wires = [w for w in spec.wires if not (w.src == G.GROUND and w.node == f"output.{n}")]
    allp = {w.port: w.src for w in wires if w.node == G.ALL_OUTPUTS}
    pictures = [w for w in wires if w.port == "image"]
    # the run: All outputs' picture back through its effects to its head
    run: list[str] = []
    head = allp.get("image")
    while _kind(head) == "effect" and head not in run:
        run.insert(0, head)
        head = _src_into(pictures, f"{head}.image")
    inside = [w.src for w in wires if w.dst == "scene.geometry" and _kind(w.src) == "hands"]
    if _kind(allp.get("hands")) == "layer":
        layer = allp["hands"]
    else:
        # the node `into` "layer" was the one not in the scene, else the first
        out_of = [k for k in sorted({1, *(h.n for h in spec.hands)})
                  if G.wired_hands_name(k) not in inside]
        layer = _layer_of(out_of[0] if out_of else 1)
    scene_guide = allp.get("guide") if inside else layer
    # `default_graph`'s output loop in words: the picture ("S" the scene's
    # run, "SH" the scene with the hands through, "H" the hands alone
    # through, ("W", src) a wire's), the hands laid over, the guide
    sw = shows
    layered = sw.hands and (not inside or not sw.scene)
    image: Any = None
    if sw.scene:
        image = "SH" if (sw.hands and sw.through and not inside) else "S"
    elif sw.hands and sw.through:
        image = "H"
    over = layer if layered and not sw.through else None
    guide = (scene_guide if (inside and sw.scene) else layer) if sw.hands else None
    own = [w for w in wires if w.node == f"output.{n}"]
    explicit_guide = any(w.port == "guide" for w in own)
    for w in own:                                      # `_Wiring._put`, wire by wire
        if w.port == "image":
            image = ("W", w.src)
            if over is None and not explicit_guide:
                guide = None
        elif w.port == "hands":
            if image in ("SH", "H"):
                image = "S" if image == "SH" else None
            over = src = w.src
            while _kind(src) in ("effect", "copy"):
                src = _src_into(pictures, f"{src}.image")
            if guide is None and _kind(src) == "layer":
                guide = src
        elif w.port == "guide":
            guide = w.src
    entries: list[dict] = []
    out: list[dict] = []
    port = f"output.{n}."
    if image is None:
        if allp.get("image") is not None:
            out.append(_w(G.GROUND, port + "image"))
    elif isinstance(image, tuple):
        out.append(_w(image[1], port + "image"))
    elif image in ("SH", "H"):
        k = _next_composite(spec)
        comp = _named("composite", k)
        entries.append(G.CompositeAt(k, spec.laid).to_json())
        if image == "SH" and head is not None:
            out.append(_w(head, f"{comp}.under"))
        out.append(_w(layer, f"{comp}.over"))
        src = comp
        aux = {w.node: w.src for w in wires if w.port == G.AUX}
        for e, c in zip(run, _next_copies(spec, len(run))):
            name = _named("copy", c)
            entries.append(G.CopyAt(c, e).to_json())
            out.append(_w(src, f"{name}.image"))
            if e in aux:
                out.append(_w(aux[e], f"{name}.aux"))
            src = name
        out.append(_w(src, port + "image"))
    said = {w.port for w in own}
    for p, want in (("hands", over), ("guide", guide)):
        # (plan 35 T3: a port the section wires itself keeps its wire though
        # All outputs' says the same — it is an override, and stays one)
        if want != allp.get(p) or (p in said and want is not None):
            out.append(_w(want if want is not None else G.GROUND, port + p))
    return [*entries, *out]

