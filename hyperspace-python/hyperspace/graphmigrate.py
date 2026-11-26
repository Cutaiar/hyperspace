"""Old loadable patches as wires, and wires back as old values (plan 33 M).

Until plan 33 an effect's place in the picture was a number: `fx.<n>.order`
in the stack, `fx.<n>.target` (the frame or the faces), and the faces' and
backdrop's channel were `view.media` / `backdrop.channel`. The free graph
says all of that as wires, so a loadable patch written before it has to be read as
wires (`to_free`, `migrate`). A save is always `hyperspace.preset/6`
(`WIRED_SCHEMA`, row 394, the owner's 2026-10-25 decision: both Macs run
the same build), so nothing here writes a graph back in older words —
the migration is one way, on load.

Pure data: it reads dicts and `graph.GraphSpec`, touches no params, loadable patch
or media module, and nothing here draws.

Rows 346 and 350 are what it keeps and what it makes:

- Only the effects that are on with mix > 0 join a run (row 346): the owner
  reads the library as using no effect that is switched off, so an off
  effect drew nothing and leaving it out changes no picture. One left out
  while something in the loadable patch drives its params is said in a load note.
- `migrate(doc, specs)` is the whole-document entry point (the section, the
  values with the retired ones dropped, any switch's select, the retargeted
  rows, the notes); `to_free(doc, specs)` is its section and notes alone.
- A route onto `view.media` or `backdrop.channel` becomes a switch over the
  eight channels (row 350), the rows retargeted onto `switch.select`.

Plan 35 M (rows 372, 383–385): then every section is a wired frame in the
owner's names — `migrate` renames it (`renamed`, V2) and writes today's
frame as wires (`wired_section`); `backdrop.history` and the look-back's
`holds` are the capture wire.

Plan 36 T2 (W2): and every edge the builder read by name — the faces'
pattern, the look-back's cover, a layer's and a guide's hands, the
scene's depth for `laid: depth` — is written as the wire it stood for
(`drawn_edges`), on every `/4`–`/6` section, a wired one too, so each
draws what it drew while nothing is read that no wire says.

Plan 36 T4 (W4): the one-shader look-back (echoes and the dream laid over
`lookback.image`, recording `lookback.capture`) is two nodes and a
composite — `split_lookback`, the last step to `/7` (`seven`), keyed on
the old values (`look_of`): on, it is `X → lookback → composite (add,
under X) → …` where the look-back sat, and `lookback → dream →` into the
composite with a dream mix above 0; off, it drew its picture untouched,
so its readers read that picture and no look-back is drawn.
"""

from __future__ import annotations

import copy
import functools
import math
import re
from dataclasses import dataclass, replace
from typing import Any

from . import graph as G
from .outputs import MAX_OUTPUTS
from .routing_sources import nsew

FREE_SCHEMA = "hyperspace.preset/5"
# plan 35 (row 385): `/6` is `/5` with the wired frame in the new ids;
# `/5` and below are read, never written
SIX_SCHEMA = "hyperspace.preset/6"
# plan 36 T3 (W3, D5): `/7` is the frame that says everything — every hidden
# edge a wire, every placement a wire, the hands entries and `laid` written,
# effects only where the section names them. What every save writes (row
# 394); a `/7` is read as it is, never migrated or filled in. `/4`–`/6` are
# read only through the one-way migration to it (`seven`)
WIRED_SCHEMA = "hyperspace.preset/7"
SEVEN = 7
# plan 40 T2 (D4, D7): `/8` is `/7` plus the GRAPH page's groups (`groups`,
# loadable.GROUPS_KEY) — written only by a loadable patch that holds one, so a loadable patch
# with none wrote `/7` byte for byte, until plan 43 C2 made every save `/9`
GROUPS_SCHEMA = "hyperspace.preset/8"
GROUPS_KEY = "groups"
# plan 43 C2 (rows 572, 576): `/9` is `/8` with the one orbit camera — the
# eye (`eye.fov`, `eye.distance`) in `values` beside `camera.*`, and the
# spin's pose (`pose`: the six `rot.phase.*`, `params.POSE_IDS`).
# What every save writes (row 521 closed: the `/7`-or-`/8` fork is gone);
# `/7` and `/8` are read through `nine`, the eye filled in on the way
EYE_SCHEMA = "hyperspace.preset/9"
NINE = 9
# plan 44 D3 (rows 611–625): `/10` is `/9` with the look made whole — the
# hands' look (`ghost.*`, but `ghost.mirror`) and the clouds' (`cloud.*`)
# in `values`, the bus cuts in `bus` (`BUS_KEY`: `graph.BusCuts`'s JSON,
# the cables from All outputs into each window this loadable patch cuts), no
# `modules` labels and no `desk_template`. What every save writes; `/9`
# and older are read through `ten`, the open show's look filled in
LOOK_SCHEMA = "hyperspace.preset/10"
# plan 57 (FQ4, the one migration): the word moves. `/11` is `/10` under the kind
# `hyperspace.loadable`, the old kind's ladder read through (`eleven`), in
# `<library>/loadable/`. A load reads both kinds until CL1; a save writes this alone.
OLD_KIND = "hyperspace.preset"
LOADABLE_KIND = "hyperspace.loadable"
ELEVEN_SCHEMA = f"{LOADABLE_KIND}/11"
ELEVEN = 11
TEN = 10
# plan 89: `/12` is `/11` with no copy node — an effect that draws on another
# picture does it by a slot of its own (`"slots"` on its entry, wires into
# `<effect>.slot.<k>.image` and out of `<effect>.slot.<k>`). What every save
# writes; `/11` and older are read through `twelve` (`slots_of_copies`)
TWELVE_SCHEMA = f"{LOADABLE_KIND}/12"
TWELVE = 12
SAVE_SCHEMA = TWELVE_SCHEMA
BUS_KEY = "bus"
# the keys `/10` retired: the module labels (row 540, the owner, 2026-11-03)
# and the desk templates (plan 24 C3: neither library held one)
TEN_RETIRED = ("modules", "desk_template")
# the look a /2 show held that /10 makes the loadable patch's (review of #351: one
# id set, one place — `library.show_look` reads it out of an old show, `ten`
# hands it to an old loadable patch): the hands' and the clouds' groups, less the
# room's mirror (`params.SHARED_META_KEYS`)
LOOK_GROUPS = ("ghost", "cloud")


def is_look_id(pid: Any) -> bool:
    """Whether `pid` is one of the look ids `/10` moved from the show into
    the loadable patch (`LOOK_GROUPS`, but `ghost[.n].mirror`)."""
    return (isinstance(pid, str) and pid.partition(".")[0] in LOOK_GROUPS
            and pid.rpartition(".")[2] != "mirror")
EYE_IDS = ("eye.fov", "eye.distance")
CAMERA_NODE = "render:camera"      # the camera's canvas id (`graphview.CAMERA`'s node)
# …and every id a file may hold it under: today's and the old canvas's (R14)
CAMERA_NODES = (CAMERA_NODE, "render:eye")


def groups_of(doc: Any) -> list:
    """Plan 40 T2, the one step from `/7` to `/8`: the key is absent → no
    groups (a `/7`, a migrated older file and a `/8` without one alike)."""
    return list(doc.get(GROUPS_KEY) or []) if isinstance(doc, dict) else []


def group_number(gid: Any) -> int:
    """`group.3` → 3; 0 for anything else (plan 40: a group's id, read by
    the loadable patch's load and by GRAPH's Group — the one rule, kept here, a
    leaf both import)."""
    head, dot, n = gid.partition(".") if isinstance(gid, str) else ("", "", "")
    return int(n) if head == "group" and dot and n.isdecimal() and int(n) >= 1 else 0


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
# the load note for an effect left out of a run while the loadable patch drives it
LEFT_OUT = "{name} was off, so it is not in the run: wire it in on GRAPH to use it"


def left_out_note(name: str) -> str:
    """The load note for effect `name` left out of a run (row 346) while
    something in the loadable patch drives one of its params."""
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
    expands (`loadable.LoadedPatch.load_doc`) — counted as its desk rows."""
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
    unreached branch; written out, the old loadable patch draws as it did."""
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
    the default frame. A section already wired is the loadable patch's own and is
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
    (a run's head). A
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
    # (plan 89: a copy is a slot before anything reads the section — a `/6`
    # wired frame may hold one; `forward` has made it one already)
    got, _, slot_notes = slots_of_copies(section)
    if got is not section:
        section = out["graph"] = got
    notes += slot_notes
    # (read against the files this build has, as the loader reads it: a
    # placement on an effect not on disk is refused there, and its effect
    # takes the run like any other)
    try:
        spec = G.read_graph(section, effects=_files(specs), placements=True)
    except G.GraphError:
        spec = None                     # the loader says so and takes the default graph
    if spec is None or spec.wired:
        # (plan 35: a wired frame is the loadable patch's own words — nothing of
        # plan 33's to add, nothing to rename; plan 36 T2: but each hidden
        # edge its builder read is written as the wire it stood for)
        for pid in [p for p in values if retired(p)]:
            del values[pid]
        if spec is not None and wire:
            out["graph"] = drawn_edges(section, _files(specs))
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
            # (row 350, R19: a loadable patch that drives a channel choice loads
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
            old = G.read_graph(sec, effects=_files(specs), placements=True)
        except G.GraphError:
            return out, notes           # (not reached: plan 33's steps write what reads)
        out["graph"] = wired_section(renamed(sec), old, backdrop_history=held_backdrop,
                                     notes=notes)
    return out, notes


def to_free(doc: dict, specs: Specs) -> tuple[dict, list[str]]:
    """The section half of `migrate`: `doc`'s `graph` section with its runs and channel wires added
    (unchanged when it already has them; `{}` for a loadable patch with no section
    and nothing to add), and the load notes. `migrate` is the rest of the
    document: the values and rows this changes.

    No production caller (a load takes the whole document, `migrate`):
    kept for tests/test_graph_migrate.py, which reads the migration's
    section on its own, one rule at a time — plan 33's rules, so the
    section as plan 33 wrote it (no wired frame: `migrate`'s `wire`)."""
    out, notes = migrate(doc, specs, wire=False)
    section = out.get("graph")
    return (section if isinstance(section, dict) else {}), notes


# ---------------------------------------------------------------- a test rig's run, as a load lands it

def specs_of(fx: Any) -> Specs:
    """An `FxState`'s effect instances as `Specs` — each one's file
    defaults, `(@order, @mix)`; none for no state. Plan 36 T3: every file
    on disk (`FxState.files`) with the instances held, so what a landed
    graph does not name is still a file the next migration reads."""
    got = {**(getattr(fx, "files", None) or {}), **(getattr(fx, "specs", None) or {})}
    # (plan 67: and a retired file, where an old stack ran it — the ladder's
    # last step makes it what replaced it)
    return {**RETIRED_SPECS, **{n: (int(sp.order), float(sp.mix)) for n, sp in got.items()}}


def state_values(fx: Any) -> dict:
    """An `FxState`'s settings as loadable patch values (`fx.on`, `fx.mix`, every
    `fx.<n>.<key>`): what a meta controller that set them by hand hands `wiring_for`."""
    out: dict[str, Any] = {"fx.on": bool(getattr(fx, "on", True)),
                           "fx.mix": float(getattr(fx, "mix", 1.0))}
    for name, v in sorted((getattr(fx, "values", None) or {}).items()):
        out.update({f"fx.{name}.{k}": x for k, x in v.items()})
    return out


def wiring_for(values: dict, specs: Specs | None = None, section: dict | None = None,
               *, wired: bool = True) -> G.Wiring:
    """The wiring a loadable patch's `values` (and its `section`, None for none)
    land as — `migrate`, the path a loadable patch load takes, read back
    (`read_graph`). Plan 33 R23: with the order-built stack gone a meta controller, a
    tool or a test that switches effects on by hand gets its run here, as
    an old loadable patch with those values would: the effects on, by `order` (the
    file's `@order` where the values name none), a faces-aimed one
    (`target` 1) onto the faces.

    Plan 35 T3: the section as plan 33 writes it (`migrate`'s `wire` off) —
    the wiring the default graph builds from the outputs' switches, which
    these rigs still set by hand until T4 retires them. Plan 36 T3: then
    wired as a load wires it (`wired_wiring`) — what a renderer takes;
    `wired` False keeps those old words (a test reading its `run`). Plan 36
    T4: its look-back as `values` had it (`look_of`)."""
    doc = {"values": dict(values)}
    if section is not None:
        doc["graph"] = section
    out, _ = migrate(doc, specs or {}, wire=False)
    section = out.get("graph")
    spec = G.read_graph(section, effects=_files(specs)) if isinstance(section, dict) else None
    got = spec.wiring() if spec is not None else G.Wiring(run=())
    return wired_wiring(got, look_of(values)) if wired else got


def wiring_of(fx: Any) -> G.Wiring:
    """`wiring_for` an `FxState` as it stands (`state_values`, `specs_of`):
    the run its switched-on effects make, by their files' `@order` — the
    one line a meta controller that sets effects by hand needs (R23). Plan 36 T3: wired
    as a load wires it (`wired_wiring`), what a renderer takes."""
    return wiring_for(state_values(fx), specs_of(fx))


# ---------------------------------------------------------------- the frame as wires (plan 35 M)
#
# Plan 35 (rows 372, 375, 383): the frame the retired `default_graph` built from the
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
    migration, not of `outputs` (T4 retired `Switches.through`)."""

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
    """The instances of `kind` (`composite`) `spec` holds: by an entry or
    by a wire's end."""
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


def _next_slots(spec: G.GraphSpec, run: list[str]) -> tuple[list[dict], list[str]]:
    """A new slot of each effect of `run` (plan 89: what plan 35's copies
    were), in order: (the effect entries that declare them — each effect's
    entry with its `slots` one up, `merge_entries` joins them to a
    section — and the slots' names). An effect at `graph.MAX_SLOTS` is a
    ValueError, in words."""
    have = {e.name: e for e in spec.effects}
    entries: dict[str, dict] = {}
    names: list[str] = []
    for name in run:
        at = have.get(name)
        if name in entries:
            k = entries[name]["slots"] + 1
        else:
            k = (at.slots if at is not None else 1) + 1
        file, n = G.split_instance(name)
        e = G.EffectAt(file, n, slots=k)          # (raises past MAX_SLOTS, in words)
        entry = {"kind": "effect", "file": file, **({"instance": n} if n != 1 else {}),
                 "slots": e.slots}
        entries[name] = entry
        names.append(G.slot_name(name, k))
    return list(entries.values()), names


def merge_entries(nodes: list, adds: list) -> list:
    """Section `nodes` with entries `adds` joined (plan 89): an effect entry
    for an instance the nodes already declare raises that entry's `slots`
    to the added one's (the rest of the entry as it is); any other is
    appended. A new list; the entries in it are new dicts where changed."""
    out = list(nodes)
    for add in adds:
        if add.get("kind") == "effect":
            key = (add.get("file"), add.get("instance", 1))
            i = next((i for i, e in enumerate(out) if isinstance(e, dict)
                      and e.get("kind") == "effect"
                      and (e.get("file"), e.get("instance", 1)) == key), None)
            if i is not None:
                slots = max(out[i].get("slots", 1), add.get("slots", 1))
                out[i] = {**out[i], **({"slots": slots} if slots != 1 else {})}
                continue
        out.append(add)
    return out


def frame_wires(spec: G.GraphSpec, *, backdrop_history: bool = False
                ) -> tuple[list[dict], list[dict]]:
    """The frame the retired `default_graph` built for `spec` under the default
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


# R14 (plan 35 T5): the GRAPH canvas's node ids before the wired frame —
# `render:<old id>`, the shared camera `render:eye` — that only an old
# layout holds (a new one says none of them), so a layout naming one is
# read in the old ids throughout: `render:hands` the layer there, the
# hands geometry in a new one
CANVAS_IDS = {"render:eye": "render:camera"}
_OLD_CANVAS = re.compile(r"render:(?:ghost(?:\.\d+)?|readout(?:\.\d+)?|history|eye|cover|"
                         r"capture|frame|fx|grounded|media\.[a-h](?:\(wire\))?|shown\(.*\)|"
                         r".*\((?:scene\+hands|hands)\))")


def renamed_canvas_id(nid: str) -> str:
    """An old canvas node id → the wired frame's (`render:ghost.2` →
    `render:hands.2`, `render:hands` → `render:hands.layer`, `render:media.a`
    → `render:channel.a`, `render:eye` → `render:camera`); any other id
    (a dissolved node's, a modifier's, a device's) as it is."""
    if nid in CANVAS_IDS:
        return CANVAS_IDS[nid]
    head, sep, name = nid.partition(":")
    if head != "render" or not sep:
        return nid
    if name.startswith("media.") and name.endswith("(wire)"):
        name = name[:-len("(wire)")]
    return f"render:{G.new_id(name)}"


def renamed_layout(layout: dict[str, Any]) -> dict[str, Any]:
    """A GRAPH layout ({node id: [x, y]}, a loadable patch's or a show's) in the
    wired frame's ids (R14): one that names an id only the old canvas had
    (`_OLD_CANVAS`) is renamed throughout (`renamed_canvas_id`), the
    first position kept where two old ids land on one; any other is as it
    is — so the owner's arrangement follows the rename, and a layout saved
    since stays put.

    Row 394: a node the wired frame dissolved (`render:frame`,
    `render:fx`, `render:capture`, `render:cover` …: an old-only id the
    rename leaves as it is) has no place on the canvas any more and is
    left out — kept, it would mark the layout old again when the save it
    is written into (always in today's ids) is read back, and a new
    `render:hands.2` would be read as the old layer's."""
    if not any(isinstance(k, str) and _OLD_CANVAS.fullmatch(k) for k in layout):
        return layout
    out: dict[str, Any] = {}
    for k, xy in layout.items():
        nk = renamed_canvas_id(k) if isinstance(k, str) else k
        if isinstance(nk, str) and _OLD_CANVAS.fullmatch(nk):
            continue                    # (a dissolved node's: nowhere to put it)
        out.setdefault(nk, xy)
    return out



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
    wire). Plan 36 T2: then the hidden edges the new wires need
    (`drawn_edges`: a window's depth for `laid: depth`) — the golden meta controller's
    word for a retired switch state over a section."""
    return drawn_edges(_output_wires_into(section, n, shows))


def _output_wires_into(section: dict, n: int, shows: Shows) -> dict:
    """`with_output_wires` less the hidden edges (`wired_section` writes
    those once, after every output)."""
    spec = G.read_graph(section, placements=True)
    got = output_wires(spec, n, shows)
    port = f"output.{n}."
    stood = {(w.src, w.dst) for w in spec.wires}
    # (plan 36 T2: the window's depth is `drawn_edges`' to say, after)
    mine = [w for w in section.get("wires", [])
            if isinstance(w, dict) and str(w.get("to", "")).startswith(port)
            and w.get("to") != port + G.DEPTH_PORT]
    refused = [w for w in mine if (w.get("from"), w.get("to")) not in stood]
    if sorted(map(str, (w for w in mine if w not in refused))) == sorted(map(str, got)):
        return section                     # (its own wires say it already: kept where they are)
    out = dict(section)
    out["nodes"] = merge_entries(section.get("nodes", []), [e for e in got if "kind" in e])
    out["wires"] = [*(w for w in section.get("wires", [])
                      if not (isinstance(w, dict) and str(w.get("to", "")).startswith(port))),
                    *(w for w in got if "kind" not in w), *refused]
    return out


# ---------------------------------------------------------------- the hidden edges as wires (plan 36 T2)
#
# Plan 36 W2: the edges a wired frame's builder read by name — the faces
# the pattern, the look-back the scene's cover, a layer and a guide their
# hands node, a composite and an output the scene's depth for the hands'
# `laid: depth` — are ports now, and a frame from before says each as the
# wire it stood for (`drawn_edges`), so it draws what it drew. (The meta controller's
# own edge, a cloud in the scene, is the meta controller's wire: `graph.cloud_wire`.)

DEPTH_PIN = "scene.depth"
COVER_PIN = "scene.cover"


def _pictures_of(section: dict, spec: G.GraphSpec) -> list[str]:
    """Every hands layer and guide `section` names, by a wire's end or an
    entry, in section order."""
    names: list[str] = []
    for w in section.get("wires") or []:
        if isinstance(w, dict):
            for x in (w.get("from"), _wire_end(w.get("to"))):
                if _kind(x) in ("layer", "guide") and x not in names:
                    names.append(x)
    for e in spec.frame_nodes:
        if isinstance(e, (G.LayerAt, G.GuideAt)) and e.name not in names:
            names.append(e.name)
    return names


def _wire_end(dst: Any) -> str | None:
    return dst.rpartition(".")[0] if isinstance(dst, str) and "." in dst else None


def drawn_edges(section: Any, files: set[str] | None = None, *, guard: bool = True) -> Any:
    """A wired `section` with each hidden edge its builder read before plan
    36 written as the wire it stood for (T2, W2), appended after its own
    wires — so a `/4`–`/6` frame draws what it drew:

    - `pattern → shape.faces`, the shape reached and its faces unwired (the
      faces drew the pattern; unwired they are plain now);
    - `scene.cover → lookback.cover`, the look-back and the scene reached
      (the look-back built its cover from the scene);
    - `hands.<n> → hands.<n>.layer.hands` / `.guide.hands`, for each layer
      and guide named with none (each drew its hands node by name);
    - with `laid: depth` and the scene reached, `scene.depth → <c>.depth`
      for each composite laid depth-aware, and into each output whose
      hands port it wires (All outputs' rides the bus to the windows).

    A wire is added only where its port has none, and (`guard`) never one
    that would close a loop; a section already saying them all is returned
    as it is (`drawn_edges` twice is once). Not a wired frame, or one the
    read refuses: as it is."""
    if not isinstance(section, dict) or section.get(G.FRAME_KEY) != G.WIRED_FRAME:
        return section
    try:
        spec = G.read_graph(section, effects=files, placements=True)
    except G.GraphError:
        return section
    raw = [w for w in section.get("wires") or [] if isinstance(w, dict)]
    into = {w.get("to") for w in raw}
    reach = G._wired_reach(spec.wires)
    add: list[dict] = []

    def put(src: str, dst: str) -> None:
        if dst not in into:
            into.add(dst)
            add.append(_w(src, dst))

    if "shape" in reach:
        put("pattern", "shape.faces")
    if "lookback" in reach and "scene" in reach:
        put(COVER_PIN, "lookback.cover")
    held = {1, *(h.n for h in spec.hands)}     # (hands 1 is always there)
    for name in _pictures_of(section, spec):
        if G.split_instance(G.hands_of(name))[1] in held:
            put(G.hands_of(name), f"{name}.hands")
    if spec.laid == "depth" and "scene" in reach:
        for c in spec.composites():
            if c.blend == "depth":
                put(DEPTH_PIN, f"{c.name}.{G.DEPTH_PORT}")
        for w in spec.wires:
            if _kind(w.node) == "output" and w.port == "hands" and w.src != G.GROUND:
                put(DEPTH_PIN, f"{w.node}.{G.DEPTH_PORT}")
    if not add:
        return section
    # (never a wire on a loop: the edge it stands for was never one either)
    every = [*spec.wires, *(G.Wire(w["from"], w["to"]) for w in add)]
    loops = G.wire_loops(every, wired=True) if guard else {}
    add = [w for w in add if G.Wire(w["from"], w["to"]) not in loops]
    if not add:
        return section
    return {**section, "wires": [*section.get("wires", []), *add]}


def _frame_loops(own: list, frame: list[dict]) -> list[tuple[dict, str]]:
    """The wires of `own` (a section's own, in order) that close a loop
    through `frame` (the frame `frame_wires` writes for it) — what plan
    34's hidden edges refused at an old section's read (`FRAME_EDGES`, the
    faces drawn in the scene, the history over the scene and the backdrop):
    the frame stands, and of the section's own the later one closing the
    loop goes, with why in words (plan 36 T2: the loop is the drawn
    frame's now, `graph.loop_words`; T3: asked of `graph.loop_closers`)."""
    stand = [G.Wire(x["from"], x["to"]) for x in frame]
    wires: list[G.Wire | None] = []
    for x in own:
        try:
            wires.append(G.Wire(x["from"], x["to"]))
        except (KeyError, TypeError, ValueError):
            wires.append(None)
    return [(own[k], why) for k, why in sorted(G.loop_closers(stand, wires).items())]


def wired_section(section: dict, spec: G.GraphSpec, *, backdrop_history: bool = False,
                  notes: list[str] | None = None) -> dict:
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
    a picture by a wire drops the guide where the hands were in the scene).

    Plan 36 T2: then each hidden edge as its wire (`drawn_edges`); and a
    wire of the section's own that closes a loop through the frame and
    its hidden edges — one plan 34's `FRAME_EDGES` refused at its read —
    is left out, said in `notes` when given (`_frame_loops`), and the
    frame is the one written for the section without it (as the read
    without it gave). Each round leaves out at least one of the section's
    own wires, so it settles within as many rounds as it has wires; one
    that did not would be a bug, and says so (T3)."""
    nodes = []
    for e in section.get("nodes") or []:
        if isinstance(e, dict) and e.get("kind") == "hands":
            e = {k: v for k, v in e.items() if k != "into"}
        elif isinstance(e, dict) and e.get("kind") in ("lookback", "history"):
            continue
        nodes.append(e)
    gone: set[tuple[Any, Any]] = set()      # the section's own wires left out (as written)
    now = spec
    rounds = len(section.get("wires") or []) + 1
    for _ in range(rounds):
        entries, frame = frame_wires(now, backdrop_history=backdrop_history)
        run = now.wiring().run
        drop = {(w.src, w.dst) for w in G._run_wires(tuple(run))} if run is not None else set()
        own, said = [], []
        for w in section.get("wires") or []:
            if isinstance(w, dict):
                pair = (w.get("from"), w.get("to"))
                if pair in drop or pair in gone:
                    continue
                w = {**w, **({"from": "lookback"} if w.get("from") == "frame" else {}),
                     **({"to": "output.all.image"} if w.get("to") == "fx.image" else {})}
                said.append(pair)
            else:
                said.append(None)
            own.append(w)
        # (the frame's hidden edges count too, as they did: `drawn_edges` of
        # the frame with the section's own wires, unguarded)
        probe = {G.FRAME_KEY: G.WIRED_FRAME, "nodes": [*nodes, *entries],
                 "wires": [*own, *frame]}
        edges = drawn_edges(probe, guard=False)["wires"][len(own) + len(frame):]
        loops = _frame_loops(own, [*frame, *edges])
        if not loops:
            break
        for w, why in loops:
            gone.add(said[next(i for i, x in enumerate(own) if x is w)])
            if notes is not None:
                notes.append(f"wire {w['from']} → {w['to']} — {why}")
        # (read again without them: the run, the look-back's picture, the
        # backdrop are the section's less what its read would refuse)
        now = replace(spec, wires=tuple(w for w in spec.wires
                                        if (G.new_id(w.src), _new_dst(w.dst)) not in gone))
    else:
        raise RuntimeError(f"wired_section: the frame did not settle in {rounds} rounds")
    out = {G.FRAME_KEY: G.WIRED_FRAME, "nodes": [*nodes, *entries], "wires": [*own, *frame]}
    outs = sorted({int(m.group(1)) for w in own if isinstance(w, dict)
                   for m in [re.fullmatch(r"output\.([1-9][0-9]*)\.[a-z]+", str(w.get("to")))]
                   if m is not None and int(m.group(1)) <= MAX_OUTPUTS})
    for n in outs:
        out = _output_wires_into(out, n, Shows())
    return drawn_edges(out)


def section_of(wiring: G.Wiring) -> dict:
    """An unwired `Wiring` (no loadable patch's graph reached it: the app before its
    first load, a test rig's, a tool's — `wiring_for`'s run) said as the
    section before the wired frame that reads as it, in the old ids (plan
    35 T4): its hands entries, `laid`, `holds`, its placed effects and the
    run's instances, its composites, then the run `frame → … → fx.image`
    (the empty one with none), the backdrop's channel and its own wires."""
    effects = list(wiring.placed)
    held = {e.name for e in effects}
    names = [*(wiring.run or ()), *(x for w in wiring.wires for x in (w.src, w.node))]
    for name in names:
        if G.wire_node_kind(name) != "effect" or name in held:
            continue
        file, n = G.split_instance(name)
        if n > 1:
            effects.append(G.EffectAt(file, n))
            held.add(name)
    # the nodes the wires name that a `Wiring` holds no entry of (the old
    # graph made each from its name): plan 33's switches, plan 34's delays,
    # resizes, look-back frames and the dream
    others: list[tuple[str, Any]] = [("composite", c) for c in wiring.composites]
    made = {"switch": G.SwitchAt, "delay": G.DelayAt, "resize": G.ResizeAt,
            "echo": G.EchoAt, "dream": lambda n: G.DreamAt()}
    seen: set[str] = set()
    for w in wiring.wires:
        for name in (w.src, w.node):
            kind = G.wire_node_kind(name)
            if kind in made and name not in seen:
                seen.add(name)
                n = name.partition(".")[2]
                others.append((kind, made[kind](int(n) if n.isdigit() else 1)))
    spec = G.GraphSpec(hands=tuple(wiring.nodes()), laid=wiring.blend,
                       history=G.HistoryAt(wiring.history), effects=tuple(effects),
                       others=tuple(others))
    out = {"nodes": spec.to_json()["nodes"],
           "wires": _chain("frame", list(wiring.run or ()), "fx.image")}
    if wiring.backdrop:
        out["wires"].append(_w(f"media.{wiring.backdrop}", "backdrop.image"))
    out["wires"] += [w.to_json() for w in wiring.wires]
    return out


def wired_of(wiring: G.Wiring, *, placements: bool = True, look: str = "off") -> dict:
    """An unwired `Wiring` (the words before the wired frame: a meta controller's, a
    tool's, a test's) as the wired frame the one-way migration writes for
    it (plan 35 T4): `section_of` it, renamed and written as a wired frame
    (`wired_section`), its look-back recording the backdrop where
    `backdrop_history` says, and (plan 36 T3) its placements as the wires
    they stood for (`placed_wires`). `Wiring()` is the factory look,
    `frame_wires(read_graph({}))` — today's frame, what a section-less old
    loadable patch migrates to. `placements` False leaves D1's entries as they are
    (the step before `placed_wires`: a test rig lays the retired switch
    states on first, as the builder placed on each output's state).
    Plan 36 T4: then the look-back split as `look` says the old values had
    it (`split_lookback`: the words hold no `dream.on`; "off", the
    default, draws no look-back) — only with `placements`, the last step."""
    section = section_of(wiring)
    out = wired_section(renamed(section), G.read_graph(section),
                        backdrop_history=wiring.backdrop_history)
    return split_lookback(placed_wires(out), look) if placements else out


def wired_wiring(wiring: G.Wiring, look: str = "off") -> G.Wiring:
    """What a renderer or `graph.build_graph` takes for `wiring` (plan 36
    T3): a wired one is itself; an unwired one is the old words, wired by
    the one-way migration (`wired_of`, its look-back as `look` says) — the
    explicit step `graph.wired` did unasked before W3."""
    return wiring if wiring.wired else _wired_wiring(wiring, look)


@functools.lru_cache(maxsize=64)
def _wired_wiring(wiring: G.Wiring, look: str = "off") -> G.Wiring:
    return G.read_graph(wired_of(wiring, look=look)).wiring()


# ---------------------------------------------------------------- D1's placements as wires (plan 36 T3)
#
# Plan 36 W3: `after` / `into` were shorthand the builder turned into edges
# on the built graph (`_place`, gone). The migration writes each as the
# wires it stood for, so a `/7` frame holds no placement and draws what the
# `/6` drew.

# the ports a wire reads something of its source through other than its
# picture (`graph.Node.REFS`: an output's readout and depth, a composite's
# depth): an effect placed after the source never sat on them
_REF_PORTS = frozenset({"guide", G.DEPTH_PORT})
PLACED_NOWHERE = "{name} {key} {where!r} — {why}: it drew nothing, so it is not wired (plan 36)"


def _insert_on(wires: list, src: str, port: str, name: str) -> list:
    """`wires` with effect `name` on the wire `src → port`: that wire (in
    its place, or appended when the section has none — a bus cable's)
    becomes `src → name.image`, then `name → port`."""
    at = next((k for k, w in enumerate(wires) if isinstance(w, dict)
               and (w.get("from"), w.get("to")) == (src, port)), None)
    new = [_w(src, f"{name}.image"), _w(name, port)]
    if at is None:
        return [*wires, *new]
    return [*wires[:at], *new, *wires[at + 1:]]


def placed_wires(section: Any, files: set[str] | None = None,
                 notes: list[str] | None = None) -> Any:
    """A wired `section` with each D1 placement written as the wires it
    stood for, and the entry's `after` / `into` dropped (plan 36 T3) —
    what the builder did on the built graph, said in wires:

    - `into` or `after` `output.<n>`: on output n's picture — its own wire
      into `output.<n>.image`, else All outputs' (the bus cable it rode);
    - `into` the look-back or an effect: on the wire into its `image`;
    - `after` a node: on its picture — `X → e.image`, and every wire that
      read X's picture (not a reference port, `_REF_PORTS`) reads `e`
      instead; after the scene while a backdrop lays it over, after the
      backdrop (plan 32 R, as the builder did).

    One placed on another placed effect is written after it, as the
    builder placed it. One with nothing to sit on (no wire into the port,
    a window that shows nothing), or one the read refuses (a name out of
    the vocabulary, a loop), drew nothing: it is left on no wire, said in
    `notes`. One after an effect that has copies sits after the original
    only (one instance is one node). Not a wired frame, one the read
    refuses, or none placed: as it is."""
    if not isinstance(section, dict) or section.get(G.FRAME_KEY) != G.WIRED_FRAME:
        return section
    try:
        spec = G.read_graph(section, effects=files, placements=True)
    except G.GraphError:
        return section
    pending = [e for e in spec.effects if e.placed]
    refused = [n for n in spec.notes if not n.startswith("wire ")]
    if notes is not None:
        # (a placement the read refused stood nowhere: its entry is kept,
        # on no wire, and said)
        notes += [f"{n}: not wired (plan 36)" for n in refused]
    if not pending and not refused:
        return section
    reached = G.reaches(spec)
    wires = list(section.get("wires") or [])

    def into(port: str) -> str | None:
        return next((w.get("from") for w in wires
                     if isinstance(w, dict) and w.get("to") == port), None)

    def nowhere(e: G.EffectAt, why: str) -> None:
        if notes is not None:
            notes.append(PLACED_NOWHERE.format(name=e.name, key=e.where[0], where=e.where[1],
                                               why=why))

    while pending:
        waiting = {e.name for e in pending}
        ready = [e for e in pending if e.where[1] not in waiting]
        if not ready:                         # (a loop: refused at the read)
            break
        for e in ready:
            pending.remove(e)
            key, where = e.where
            if where.startswith("output."):
                port = f"{where}.image"
                src = into(port) or into(f"{G.ALL_OUTPUTS}.image")
                if src is None or src == G.GROUND:
                    nowhere(e, f"output {where.partition('.')[2]} shows no picture")
                    continue
                wires = _insert_on(wires, src, port, e.name)
            elif key == "into":
                port = f"{where}.image"
                src = into(port)
                if src is None:
                    nowhere(e, f"nothing goes into {port}")
                    continue
                wires = _insert_on(wires, src, port, e.name)
            else:
                node = G.BACKDROP if where == "scene" and G.BACKDROP in reached else where
                read = [k for k, w in enumerate(wires) if isinstance(w, dict)
                        and w.get("from") == node
                        and str(w.get("to")).rpartition(".")[2] not in _REF_PORTS]
                for k in read:
                    wires[k] = {**wires[k], "from": e.name}
                at = read[0] if read else len(wires)
                wires.insert(at, _w(node, f"{e.name}.image"))
    nodes = [{k: v for k, v in n.items() if k not in G.PLACE_KEYS}
             if isinstance(n, dict) and n.get("kind") == "effect" else n
             for n in section.get("nodes") or []]
    return {**section, "nodes": nodes, "wires": wires}


# ---------------------------------------------------------------- the one-way migration to /7 (plan 36 T3)

def schema_version(doc: Any) -> int | None:
    """The `n` of a loadable patch document's `hyperspace.preset/<n>`, else None."""
    schema = doc.get("schema") if isinstance(doc, dict) else None
    if not isinstance(schema, str):
        return None
    _, _, v = schema.rpartition("/")
    return int(v) if v.isdigit() else None


def section_effects(section: Any) -> set[str]:
    """Every effect instance a wired `section` names — by an entry, a wire's
    end, or (a section not yet through `twelve`) a copy's `of` — the effects
    that exist in its loadable patch (W3)."""
    out: set[str] = set()
    if not isinstance(section, dict):
        return out
    for e in section.get("nodes") or []:
        if not isinstance(e, dict):
            continue
        if e.get("kind") == "effect" and isinstance(e.get("file"), str):
            n = e.get("instance", 1)
            out.add(G.instance_name(e["file"], n if isinstance(n, int) else 1))
        elif e.get("kind") == "copy" and isinstance(e.get("of"), str):
            out.add(e["of"])
    for w in section.get("wires") or []:
        if isinstance(w, dict):
            for name in (w.get("from"), _wire_end(w.get("to"))):
                if _kind(name) == "effect":
                    out.add(name)
    return out


MIGRATED_NOTE = "{old} migrated to {new} (plan 36): every edge drawn as it ran — save to keep it"
SLOTS_MIGRATED_NOTE = ("{old} migrated to {new} (plan 89): each copy is a slot of its effect "
                       "now — save to keep it")


# ---------------------------------------------------------------- the one orbit camera (plan 43 C2)

def nine(doc: dict, eye: dict | None = None, camera_at: Any = None) -> dict:
    """An older loadable patch (before `/9`) as its `/9` reads it — pure, one way,
    on load (`LoadedPatch.load_doc`) and so in tools/migrate_library.py's
    resave: the eye written into `values` from `eye` (the open show's
    `session`, read out of an old show by `library.Install`; an id it lacks
    is left out, and the load fills it from the build's default), and the
    camera node's GRAPH position from `camera_at` (the old show's layout
    entry, ``render:camera``) into the loadable patch's `layout` where the file
    places it nowhere. A value or a position the file already has stays;
    no pose is added (an old file keeps spinning: row 573). A `/9` and
    anything that is not a document come back as they are."""
    version = schema_version(doc)
    if not isinstance(doc, dict) or (version is not None and version >= NINE):
        return doc
    out = dict(doc)
    eye = {pid: v for pid, v in dict(eye or {}).items()
           if pid in EYE_IDS and isinstance(v, (int, float)) and not isinstance(v, bool)}
    raw = out.get("values")
    # (a `values` that is no map is not this step's to judge: it is left as
    # it is, and the load's own reading of `values` refuses or reads it)
    if eye and (raw is None or isinstance(raw, dict)):
        values = dict(raw or {})
        for pid, v in eye.items():
            values.setdefault(pid, v)
        out["values"] = values
    layout = out.get("layout")
    if camera_at is not None and (layout is None or isinstance(layout, dict)):
        layout = dict(layout or {})
        if not any(k in layout for k in CAMERA_NODES):
            layout[CAMERA_NODE] = list(camera_at)
            out["layout"] = layout
    return out


def ten(doc: dict, look: dict | None = None, cuts: Any = None) -> dict:
    """An older loadable patch (before `/10`) as its `/10` reads it (plan 44 D3) —
    pure, one way, on load (`LoadedPatch.load_doc`, after `nine`) and so in
    tools/migrate_library.py's resave: the hands' and the clouds' looks
    written into `values` from `look` (what the open show's `session` held,
    `library.Install.old_look`: an id the file already names stays, an id
    neither names takes the build's default at the load), the bus cuts into
    `bus` from `cuts` (the open show's `rig`, a `graph.BusCuts`; a file
    that names its own keeps them), and the retired keys (`TEN_RETIRED`:
    the module labels, a desk template's name) dropped. A `/10` and
    anything that is not a document come back as they are."""
    version = schema_version(doc)
    if not isinstance(doc, dict) or (version is not None and version >= TEN):
        return doc
    out = {k: v for k, v in doc.items() if k not in TEN_RETIRED}
    if doc.get("desk_template") and isinstance(out.get("desk"), list):
        # a templated desk's `dark` rows only said "not the template's row
        # here": with no template they say nothing (the overrides are the desk)
        out["desk"] = [r for r in out["desk"]
                       if not (isinstance(r, dict) and r.get("dark") is True)]
    look = {pid: v for pid, v in dict(look or {}).items()
            if is_look_id(pid) and isinstance(v, (int, float, bool))}
    raw = out.get("values")
    # (a `values` that is no map is the load's to judge, as in `nine`)
    if look and (raw is None or isinstance(raw, dict)):
        values = dict(raw or {})
        for pid, v in look.items():
            values.setdefault(pid, v)
        out["values"] = values
    got = cuts.to_json() if isinstance(cuts, G.BusCuts) else {}
    if got and BUS_KEY not in out:
        out[BUS_KEY] = got
    return out


# ---------------------------------------------------------------- the look-back split (plan 36 T4)
#
# Plan 36 W4: the look-back was one object — a ring of echoes and the dream
# buffer, laid over `lookback.image` in one shader, recording
# `lookback.capture`, all of it gated by `dream.on`. Since `/7` a look-back
# records its `image` and makes its trail; the dream dreams its `image`; a
# composite lays them on. An old frame is rewritten so (`split_lookback`).

LOOKS = ("off", "trail", "dream")   # the old look-back: off, echoes alone, echoes + dream
OLD_MIX = 0.7                       # dream.mix's default, for a file that leaves it out


def look_of(values: dict | None) -> str:
    """What an old file's look-back drew (`LOOKS`), by its values: off
    without `dream.on`; with it, the dream too when `dream.mix` is above 0
    (whether a worker is enabled is the config's, never the loadable patch's), else
    the echoes alone."""
    vals = values or {}
    if vals.get("dream.on") is not True:
        return "off"
    try:
        mix = float(vals.get("dream.mix", OLD_MIX))
    except (TypeError, ValueError):
        mix = OLD_MIX
    return "dream" if mix > 0.0 else "trail"


# the load note for a file whose `dream.on` or `dream.mix` something drives
# (a pad toggling the tracers live): the chain is drawn, and the switch is
# the dream's alone from here on
LIVE_LOOK_NOTES = {
    "dream.on": ("dream.on is driven: dream.on now switches only the dream; the trail is "
                 "the drawn look-back (plan 36)"),
    "dream.mix": ("dream.mix is driven from 0: the dream is drawn so it can be pushed in "
                  "(plan 36)"),
}


def live_look_of(values: dict | None, driven: frozenset[str] | set[str]) -> tuple[str, list[str]]:
    """`look_of` with what the file drives counted (plan 36 final review):
    a route, desk row or macro subscriber on `dream.on` drew the look-back
    whenever it switched it on, so the chain is drawn whatever its rest
    value — with the dream while `dream.mix` is above 0 or driven; one on
    `dream.mix` at 0 at rest draws the dream too. (the look, the driven
    ids that changed it — each said with its `LIVE_LOOK_NOTES`)"""
    vals = values or {}
    look = look_of(vals)
    try:
        mix = float(vals.get("dream.mix", OLD_MIX))
    except (TypeError, ValueError):
        mix = OLD_MIX
    on_driven = "dream.on" in driven
    mix_driven = "dream.mix" in driven and mix <= 0.0
    live: list[str] = []
    if on_driven:
        live.append("dream.on")
        if look == "off":
            look = "dream" if mix > 0.0 or "dream.mix" in driven else "trail"
    if mix_driven and look != "off":
        if look == "trail":
            look = "dream"
        live.append("dream.mix")
    return look, live


def _next_composite_of(nodes: list) -> int:
    held = {int(n.get("instance", 1)) for n in nodes
            if isinstance(n, dict) and n.get("kind") == "composite"}
    k = 1
    while k in held:
        k += 1
    return k


def split_lookback(section: Any, look: str) -> Any:
    """An old wired `section`'s one-shader look-back as the two nodes
    since `/7` (plan 36 T4, W4) — the last step of the migration (after
    `placed_wires`: a placement `into` the look-back sat on its old picture),
    applied once, to an old frame only. `look` is what it drew (`look_of`):

    - "trail" or "dream": what was recorded (`lookback.capture`) goes into
      `lookback.image`; the old picture under (`lookback.image`) into a new
      composite's `under` (blend add: the trail added on, the old shader's
      arithmetic) and into `lookback.occluder` (the old default: its own
      picture's brightness held the wake back) unless one was wired; the
      cover stays; `lookback` into the composite's `over` — or with
      "dream" `lookback → dream.image` and `dream` there; every reader of
      the old look-back reads the composite.
    - "off": the old look-back drew its picture untouched — its readers
      read that picture, and no look-back is drawn — unless a frame of its
      ring is read (plan 34's `echo.<k>`): then the look-back still
      records, and only those read it.

    Plan 34's `echo.<k>` entries go: each wire from one reads the
    look-back's pin `lookback.echo.<k>`. Plan 34's `dream` (the buffer
    alone) is the dream node, fed the look-back's trail while one is drawn,
    else what the look-back recorded (no look-back drawn just to feed it). Not a wired frame,
    or one with no look-back: as it is."""
    if look not in LOOKS:
        raise ValueError(f"look {look!r}: one of {', '.join(LOOKS)}")
    if not isinstance(section, dict) or section.get(G.FRAME_KEY) != G.WIRED_FRAME:
        return section
    raw = list(section.get("wires") or [])
    nodes = list(section.get("nodes") or [])
    wires = [w for w in raw if isinstance(w, dict)]

    def into(port: str) -> Any:
        return next((w.get("from") for w in wires if w.get("to") == port), None)

    def old_echo(name: Any) -> bool:
        return (isinstance(name, str) and name.startswith("echo.")
                and name.partition(".")[2].isdecimal())

    echoes = [n for n in nodes if isinstance(n, dict) and n.get("kind") == "echo"]
    dreams = [n for n in nodes if isinstance(n, dict) and n.get("kind") == "dream"]
    dream_read = bool(dreams) and any(w.get("from") == "dream" for w in wires)
    ring_read = any(old_echo(w.get("from")) for w in wires)
    touches = any(str(w.get("to", "")).startswith("lookback.") or w.get("from") == "lookback"
                  for w in wires)
    if not touches and not ring_read and not dream_read and not echoes:
        return section
    under, held = into("lookback.image"), into("lookback.capture")
    occ, cover = into("lookback.occluder"), into("lookback.cover")
    live = look in ("trail", "dream")
    dreaming = look == "dream" or dream_read
    nodes = [n for n in nodes if not (isinstance(n, dict) and n.get("kind") in ("lookback", "echo"))]
    # the new wires, each group where its old one stood (the canonical
    # frame order, `graphview._frame_order`): the trail laid on where the
    # picture under it was wired, the record where the capture was, the
    # cover where it was
    lay: list[dict] = []
    record = [_w(held, "lookback.image")] if (live or ring_read) and held is not None else []
    covered = [_w(cover, "lookback.cover")] if live and cover is not None else []
    head = under
    if live:
        if occ or under:
            lay.append(_w(occ or under, "lookback.occluder"))
        k = _next_composite_of(nodes)
        comp = G.CompositeAt(k, "add")
        nodes.append(comp.to_json())
        if under is not None:
            lay.append(_w(under, f"{comp.name}.under"))
        if look == "dream":
            lay += [_w("lookback", "dream.image"), _w("dream", f"{comp.name}.over")]
        else:
            lay.append(_w("lookback", f"{comp.name}.over"))
        head = comp.name
    if dreaming and not any(w.get("to") == "dream.image" for w in lay):
        # (fix round 1, M1: plan 34's dream read the buffer of what was
        # recorded — with no look-back drawn, the dream dreams that picture
        # itself; with one drawn, its trail)
        src = "lookback" if (live or ring_read) else (held or under)
        if src is not None:
            lay.append(_w(src, "dream.image"))
    if dreaming and not dreams:
        nodes.append(G.DreamAt().to_json())
    at = {"lookback.image": lay, "lookback.capture": record, "lookback.cover": covered}
    out: list[Any] = []
    for w in raw:
        if not isinstance(w, dict):
            out.append(w)
            continue
        to = str(w.get("to", ""))
        if to.startswith("lookback."):
            out += at.pop(to, [])
            continue
        if w.get("from") == "lookback":
            if head is None:
                continue                  # (it drew nothing over nothing: the port is unwired)
            w = {**w, "from": head}
        elif old_echo(w.get("from")):
            w = {**w, "from": f"lookback.echo.{w['from'].partition('.')[2]}"}
        out.append(w)
    for rest in at.values():                  # (an old wire the frame did not have)
        out += rest
    return {**section, "nodes": nodes, "wires": out}


def seven(doc: dict, specs: Specs, *, desk: list | None = None) -> tuple[dict, list[str]]:
    """Plan 36 T3 (W3, D5): the one-way migration of a `/4`–`/6` document
    (or older: what the loader takes) to `/7` — (the document, the notes).
    `migrate` (the free graph, the wired frame, every hidden edge as its
    wire; a document with no section gets today's frame), then each D1
    placement as the wires it stood for (`placed_wires`), and the values of
    every effect the section does not name dropped (instance 1 of a file
    exists only where the section names it). The hands entries and `laid`
    are the section's own words from here on: a save writes them all
    (`graph.GraphSpec.to_json`). Its `schema` is `WIRED_SCHEMA`; a section
    the read refuses is left as it is (the loader says so).

    A `/7` document is never handed here: what it says is all there is. A
    pure function of the old document (and the build's effect files), so
    tools/migrate_library.py and a load write the same `/7`.

    Plan 36 T4 (W4): last, the look-back split into its two nodes and a
    composite (`split_lookback`, by `look_of` the file's values — and by
    what it drives, `live_look_of`: a driven `dream.on`, or a driven
    `dream.mix` at 0, draws the chain, said), and `dream.on` — which gated
    the whole look-back — is the dream's own switch: on exactly when the
    split drew a dream, but for a driven one, whose rest value stands."""
    out, notes = migrate(doc, specs, desk=desk)
    section = out.get("graph")
    if isinstance(section, dict) and section.get(G.FRAME_KEY) == G.WIRED_FRAME:
        try:
            G.read_graph(section, effects=_files(specs), placements=True)
        except G.GraphError:
            pass                            # (unreadable: the loader says so)
        else:
            section = placed_wires(section, _files(specs), notes)
            values = _values(out)
            look, live = live_look_of(values, targets(out, desk))
            notes += [LIVE_LOOK_NOTES[pid] for pid in live]
            section = out["graph"] = split_lookback(section, look)
            dreams = any(isinstance(n, dict) and n.get("kind") == "dream"
                         for n in section.get("nodes") or [])
            if "dream.on" in live and dreams:
                # (what drives it switches the dream: its rest value stands)
                values["dream.on"] = values.get("dream.on") is True
            elif dreams or "dream.on" in values:
                values["dream.on"] = dreams
            held = section_effects(section)
            for pid in [p for p in values if effect_of(p) not in (None, *held)]:
                del values[pid]
    out["schema"] = WIRED_SCHEMA
    return out, notes


def _src_into(wires, dst: str) -> str | None:
    return next((w.src for w in wires if w.dst == dst), None)


def _kind(name: str | None) -> str | None:
    return G.wire_node_kind(name, wired=True) if name is not None else None


def output_wires(spec: G.GraphSpec, n: int, shows: Shows) -> list[dict]:
    """Output `n`'s overrides of All outputs under `shows` (plan 35 M):
    exactly the picture, hands and guide the retired `default_graph` gave output `n`
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
    the layer over) and a new slot of each effect of All outputs' run
    (none for an empty run; plan 89, a copy before it), `composite.k →
    acid.slot.k → … → output.<n>.image`, each slot with its effect's aux
    wire, its effect's entry carrying the slot (`merge_entries`); whether it bends is the
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
            while _kind(src) in ("effect", "slot"):
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
        made, slots = _next_slots(spec, run)
        entries += made
        for e, name in zip(run, slots):
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



def through_wires(spec: G.GraphSpec, n: int, bus_cuts: G.BusCuts | None = None) -> list[dict]:
    """OUTPUT's "hands through the effects" on window `n` as the wires it
    names (plan 36 T1, the live edit — `output_wires` stays the migration's
    word for the retired switch): a `composite.k` (the lowest free
    instance, its blend the hands' `laid`) laying All outputs' hands layer
    `over` the head of All outputs' picture (behind its run; nothing
    `under` while the window's picture is `ground`: the hands alone), one
    new slot of each effect of that run (plan 89), each with its effect's
    aux wire, `composite.k → acid.slot.k → … → output.<n>.image` (the
    effects' entries carrying the slots: `merge_entries`), and `ground →
    output.<n>.hands` — the layer goes through, not over again. Nothing
    else: the guide, and every other wire of `spec`, are left as they are.
    Entries first (the dicts with `kind`), then the wires. `spec` is a
    wired frame whose All outputs lays a hands layer on (the page refuses
    otherwise, `graphview.through_refusal`). `rig` (plan 36 T1): the bus
    cables standing — a window with no picture of its own and its picture
    cable cut counts as `ground` (the page refuses that too)."""
    wires = spec.wires
    allp = {w.port: w.src for w in wires if w.node == G.ALL_OUTPUTS}
    pictures = [w for w in wires if w.port == "image"]
    # (plan 89: All outputs' run back through its effects and their slots —
    # each pass by its own name, for its own input and aux wire)
    run: list[str] = []
    head = allp.get("image")
    while _kind(head) in ("effect", "slot") and head not in run:
        run.insert(0, head)
        head = _src_into(pictures, f"{head}.image")
    port = f"output.{n}."
    own = _src_into(wires, port + "image")
    alone = own == G.GROUND or (own is None and bus_cuts is not None
                                and not bus_cuts.has(G.bus_wire(n, "image")))
    k = _next_composite(spec)
    comp = _named("composite", k)
    entries = [G.CompositeAt(k, spec.laid).to_json()]
    out: list[dict] = []
    if head is not None and not alone:
        out.append(_w(head, f"{comp}.under"))
    out.append(_w(allp["hands"], f"{comp}.over"))
    if spec.laid == "depth" and "scene" in G._wired_reach(wires):
        # plan 36 T2: laid depth-aware against the scene's depth, as a wire
        out.append(_w(DEPTH_PIN, f"{comp}.{G.DEPTH_PORT}"))
    src = comp
    aux = {w.node: w.src for w in wires if w.port == G.AUX}
    made, slots = _next_slots(spec, [G.effect_of(p) for p in run])
    entries += made
    for e, name in zip(run, slots):
        out.append(_w(src, f"{name}.image"))
        if e in aux:
            out.append(_w(aux[e], f"{name}.aux"))
        src = name
    out += [_w(src, port + "image"), _w(G.GROUND, port + "hands")]
    return [*entries, *out]


# ---------------------------------------------------------------- copies as slots (plan 89)

COPY_DROPPED = ("{name}: a copy of {of!r}, which is no effect instance of this graph — "
                "dropped with its wires (plan 89)")
COPY_PAST_SLOTS = ("{name}: a copy of {of}, past the {most} slots one effect has — dropped "
                   "with its wires (plan 89)")


def copy_name(e: Any) -> str | None:
    """A `copy` entry's node name (`copy`, `copy.2`), None for a bad instance."""
    n = e.get("instance", 1)
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return None
    return "copy" if n == 1 else f"copy.{n}"


def slots_of_copies(section: Any) -> tuple[Any, dict[str, str], list[str]]:
    """A graph section (a loadable patch's, or a patch fragment's nodes and
    wires — any dict with `nodes` and `wires`) with every `copy` entry
    made a slot of the effect it drew again (plan 89, the one way): (the
    section, a copy's name → its slot's name, the notes).

    The rule: a section's copies of one effect instance, lowest copy
    instance first, become that effect's next slots — `copy` of `acid`
    with `acid` holding one slot is `acid.slot.2`, the next copy of `acid`
    `acid.slot.3`. The effect's entry says `slots` (an entry is added for
    an effect only its wires named); every wire end naming the copy (its
    picture out, its `image` and `aux` in) and a `keys` member names the
    slot. A slot runs the effect on its own picture with the one set of
    knobs and clock, as the copy did (`graph.Slot` is the pass a
    `graph.Copy` was), so the picture is the same. A copy of no effect the
    section holds (one the read dropped, said) and one past
    `graph.MAX_SLOTS` are dropped with their wires, said. Anything that is
    no section, or holds no copy, comes back as it is."""
    if not isinstance(section, dict) or not isinstance(section.get("nodes"), list):
        return section, {}, []
    copies = [e for e in section["nodes"] if isinstance(e, dict) and e.get("kind") == "copy"]
    if not copies:
        return section, {}, []
    wires = [w for w in section.get("wires") or [] if isinstance(w, dict)]
    held = {G.instance_name(e["file"], e.get("instance", 1)) for e in section["nodes"]
            if isinstance(e, dict) and e.get("kind") == "effect" and isinstance(e.get("file"), str)
            and isinstance(e.get("instance", 1), int)}
    held |= {name for w in wires for name in (w.get("from"), _wire_end(w.get("to")))
             if _kind(name) == "effect"}
    notes: list[str] = []
    renames: dict[str, str] = {}
    dropped: set[str] = set()
    adds: list[dict] = []
    slots: dict[str, int] = {}
    for e in section["nodes"]:
        if isinstance(e, dict) and e.get("kind") == "effect" and isinstance(e.get("file"), str):
            n = e.get("instance", 1)
            k = e.get("slots", 1)
            if isinstance(n, int) and isinstance(k, int):
                slots[G.instance_name(e["file"], n)] = k

    def order(e: dict) -> int:
        n = e.get("instance", 1)
        return n if isinstance(n, int) and not isinstance(n, bool) else 0

    for e in sorted(copies, key=order):
        name, of = copy_name(e), e.get("of")
        if name is None:
            continue                        # (no copy the read ever made: its wires named nothing)
        if not isinstance(of, str) or of not in held or _kind(of) != "effect":
            notes.append(COPY_DROPPED.format(name=name, of=of))
            dropped.add(name)
            continue
        k = slots.get(of, 1) + 1
        if k > G.MAX_SLOTS:
            notes.append(COPY_PAST_SLOTS.format(name=name, of=of, most=G.MAX_SLOTS))
            dropped.add(name)
            continue
        slots[of] = k
        renames[name] = G.slot_name(of, k)
        file, n = G.split_instance(of)
        adds.append({"kind": "effect", "file": file, **({"instance": n} if n != 1 else {}),
                     "slots": k})
    out = dict(section)
    out["nodes"] = merge_entries([e for e in section["nodes"]
                                  if not (isinstance(e, dict) and e.get("kind") == "copy")], adds)

    def end(name: Any) -> Any:
        return renames.get(name, name)

    new_wires = []
    for w in section.get("wires") or []:
        if not isinstance(w, dict):
            new_wires.append(w)
            continue
        src, dst = w.get("from"), w.get("to")
        node = _wire_end(dst)
        if src in dropped or node in dropped:
            continue
        w = dict(w)
        if isinstance(src, str):
            w["from"] = end(src)
        if isinstance(dst, str) and node in renames:
            w["to"] = f"{renames[node]}.{dst.rpartition('.')[2]}"
        new_wires.append(w)
    if "wires" in section:
        out["wires"] = new_wires
    if isinstance(section.get(G.KEYS_KEY), list):
        out[G.KEYS_KEY] = [end(k) for k in section[G.KEYS_KEY] if k not in dropped]
    return out, renames, notes


def retarget_copies(obj: Any, renames: dict[str, str]) -> Any:
    """`obj` (a document's values, rows, node mode … — anything but its
    graph) with what named a migrated copy naming its slot (plan 89): its
    black-is-clear knobs `key.<copy>.*` → `key.<slot>.*` (keys of a map, and
    any text, a row's target say), and a canvas node `render:<copy>` (node
    mode's target) → `render:<effect>`, the node the slot is drawn on. A
    copy instance's ids never take another's (`key.copy.2.*` is not
    `copy`'s). A copy where anything changed, else `obj` itself."""
    if not renames:
        return obj
    order = sorted(renames, key=len, reverse=True)

    def one(x: str) -> str:
        for old in order:
            new = renames[old]
            if x == f"render:{old}":
                return f"render:{G.effect_of(new)}"
            head = f"key.{old}"
            if x == head:
                return f"key.{new}"
            if x.startswith(head + ".") and not x[len(head) + 1:][:1].isdigit():
                return f"key.{new}" + x[len(head):]
        return x

    def walk(v: Any) -> Any:
        if isinstance(v, str):
            return one(v)
        if isinstance(v, dict):
            return {(one(k) if isinstance(k, str) else k): walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    got = walk(obj)
    return obj if got == obj else got


def twelve(doc: dict) -> tuple[dict, list[str]]:
    """An older loadable patch (before `/12`) as its `/12` reads it (plan
    89) — pure, one way, on load: its graph section's copies made slots
    (`slots_of_copies`), and the copies' GRAPH places and group
    memberships (`render:copy.<n>`) dropped — a slot is drawn on its
    effect's node, which has its own place. The schema is left to the
    ladder (`forward`). (the document, the notes)"""
    section = doc.get("graph") if isinstance(doc, dict) else None
    got, renames, notes = slots_of_copies(section)
    if got is section or not isinstance(section, dict):
        return doc, []
    # (plan 89: every other key's mentions of a copy — its `key.<copy>.*`
    # knobs in values and rows, node mode's `render:<copy>` — the slot's)
    out = {k: (v if k in ("graph", "layout", GROUPS_KEY, "schema", "name")
               else retarget_copies(v, renames)) for k, v in doc.items()}
    out["graph"] = got
    gone = {f"render:{name}" for name in renames} | {
        f"render:{copy_name(e)}" for e in section["nodes"]
        if isinstance(e, dict) and e.get("kind") == "copy" and copy_name(e)}
    if isinstance(doc.get("layout"), dict):
        out["layout"] = {k: v for k, v in doc["layout"].items() if k not in gone}
    if isinstance(doc.get(GROUPS_KEY), list):
        out[GROUPS_KEY] = [{**g, "nodes": [x for x in g["nodes"] if x not in gone]}
                           if isinstance(g, dict) and isinstance(g.get("nodes"), list) else g
                           for g in doc[GROUPS_KEY]]
    return out, notes


# ---------------------------------------------------------------- Hue cycle retired (plan 67)

# the owner, 2026-11-25 ("migrate exactly, new ops"; "new op: Hue turn"): Hue
# cycle hid a field — its bands, `mix(p.x + p.y, 2 |p|, Rings) × Spread`, in
# turns, frame heights from the middle — and turned the hues by it. Its bands
# are field nodes now, wired into Hue turn's Turn at a depth of 360 (degrees a
# turn): Line (45°, Scale √2: p.x + p.y) and Rings (Scale 2: 2 |p|), each
# weighted by a Scale (1 − Rings, Rings), added (Combine), × Spread (a Scale,
# so a route on Spread keeps a knob to land on). The picture is Hue cycle's to
# the GPU's rounding (`tests/test_hue_turn.py`). Keyed on the file, not a
# schema: a document still naming `huecycle`, of any version, is rewritten on
# load (`retire_hue_cycle`), so no schema moves (DECISIONS)
HUE_CYCLE, HUE_TURN = "huecycle", "hueturn"
HUE_CYCLE_DEFAULTS = {"spread": 0.8, "rings": 0.5}
# the retired files' (@order, @mix), so the steps before the retirement still
# place one where an old stack ran it (`forward`'s `specs`)
RETIRED_SPECS: dict[str, tuple[int, float]] = {HUE_CYCLE: (85, 1.0)}
HUE_TURN_DEPTH = 360.0
HUE_SPREAD_SPAN = 4.0            # Spread ran 0 … 4; the band's Scale × runs −4 … 4
HUE_TURN_NOTE = ("{old} is Hue turn now ({new}): Hue cycle is retired (plan 67), its bands "
                 "Line, Rings, Scale and Combine wired into Turn — the same picture; save to keep it")
HUE_ABS_NOTE = ("{row}: a row that placed Hue cycle's Spread (0 … 4) places the bands' Scale × "
                "now (−4 … 4): its middle is still, below it the bands turn the other way")
HUE_RINGS_NOTE = ("{row}: Hue cycle's Rings is two Scales of the bands now (1 − Rings and "
                  "Rings), so this row is left out")
_HUE_BASE = re.compile(r"^huecycle(?:\.(\d+))?(?=\.|$)")
_HUE_PARAM = re.compile(r"^fx\.huecycle(?:\.(\d+))?\.([a-z_][a-z0-9_]*)$")
_ROW_LISTS = ("routes", "desk", "bindings")


def _effect_base(name: str) -> str:
    """`scale.2.image` → `scale.2`; `hueturn.slot.2` → `hueturn`: the effect
    instance a wire's end names."""
    parts = name.split(".")
    return parts[0] + (f".{parts[1]}" if len(parts) > 1 and parts[1].isdigit() else "")


def _hue_old(name: Any) -> str | None:
    """The Hue cycle instance `name` names (`huecycle.2.image` → `huecycle.2`), or None."""
    m = _HUE_BASE.match(name) if isinstance(name, str) else None
    return m.group(0) if m else None


def retire_hue_cycle(nodes: list, wires: list, rest: dict, ports: list | None = None
                     ) -> tuple[list, list, dict, list | None, list[str]]:
    """A section's `nodes` and `wires`, the document's other keys (`rest`:
    values, rows, macros, layout, groups, node mode …) and a fragment's
    `ports`, with every Hue cycle made Hue turn and its bands' field nodes
    (plan 67; module notes above) — (nodes, wires, rest, ports, notes). Pure:
    the inputs are untouched, and handed back as they are when no Hue cycle is
    named. A row onto Spread lands on the bands' × (a push's depth halved, the
    range being twice as wide; a set's norm moved onto it; an abs desk row
    kept, said: `HUE_ABS_NOTE`); a row onto Rings is left out, said."""
    olds: list[str] = []
    for e in nodes:
        if isinstance(e, dict) and e.get("kind") == "effect" and e.get("file") == HUE_CYCLE:
            n = e.get("instance", 1)
            olds.append(G.instance_name(HUE_CYCLE, n if isinstance(n, int) else 1))
    for w in wires:
        if isinstance(w, dict):
            for end in (w.get("from"), w.get("to")):
                got = _hue_old(end)
                if got is not None and got not in olds:
                    olds.append(got)
    drawn = set(olds)
    # (one named only by its knobs — off, out of an old stack's run — is
    # renamed, its knobs kept, and gets no bands: nothing draws it)
    for k in _hue_params(rest):
        m = _HUE_PARAM.match(k)
        got = G.instance_name(HUE_CYCLE, int(m.group(1)) if m.group(1) else 1) if m else None
        if got is not None and got not in olds:
            olds.append(got)
    if not olds:
        return nodes, wires, rest, ports, []
    taken: set[str] = set()
    for e in nodes:
        if isinstance(e, dict) and isinstance(e.get("file"), str):
            n = e.get("instance", 1)
            taken.add(G.instance_name(e["file"], n if isinstance(n, int) else 1))
    for w in wires:
        if isinstance(w, dict):
            for end in (w.get("from"), w.get("to")):
                if isinstance(end, str):
                    taken.add(_effect_base(end))

    def free(file: str) -> str:
        n = 1
        while G.instance_name(file, n) in taken:
            n += 1
        name = G.instance_name(file, n)
        taken.add(name)
        return name

    def entry(name: str, like: dict | None = None) -> dict:
        file, n = G.split_instance(name)
        out = {k: v for k, v in (like or {"kind": "effect"}).items() if k != "instance"}
        out.update(kind="effect", file=file)
        if n != 1:
            out["instance"] = n
        return out

    renames = {old: free(HUE_TURN) for old in olds}
    values = dict(rest.get("values") or {}) if isinstance(rest.get("values"), dict) else {}
    knobs: dict[str, dict[str, Any]] = {old: {} for old in olds}
    for k in list(values):
        m = _HUE_PARAM.match(k)
        if m is None:
            continue
        old = G.instance_name(HUE_CYCLE, int(m.group(1)) if m.group(1) else 1)
        knobs.setdefault(old, {})[m.group(2)] = values.pop(k)
    out_nodes = [entry(renames[G.instance_name(HUE_CYCLE, e.get("instance", 1))], e)
                 if isinstance(e, dict) and e.get("kind") == "effect" and e.get("file") == HUE_CYCLE
                 else e for e in nodes]

    def rename(x: Any) -> Any:
        old = _hue_old(x)
        return renames[old] + x[len(old):] if old in renames else x
    out_wires = [{**w, "from": rename(w.get("from")), "to": rename(w.get("to"))}
                 if isinstance(w, dict) else w for w in wires]
    # (a field once wired into Spread or Rings — a knob then — goes where that
    # knob is now: Spread the bands' ×, Rings its two weights; Devin on #509)
    knob_fields = [w for w in out_wires if isinstance(w, dict) and isinstance(w.get("to"), str)
                   and w["to"].rpartition(".")[2] in HUE_CYCLE_DEFAULTS
                   and w["to"].rpartition(".")[0] in renames.values()]
    out_wires = [w for w in out_wires if not any(w is k for k in knob_fields)]
    notes: list[str] = []
    band: list[dict] = []
    spread_to: dict[str, str] = {}      # a Hue cycle → its bands' × (`fx.scale.<n>.mul`)
    for old in olds:
        if old not in drawn:
            values.update({f"fx.{renames[old]}.{k}": v for k, v in knobs.get(old, {}).items()
                           if k not in HUE_CYCLE_DEFAULTS})
            notes.append(HUE_TURN_NOTE.format(old=old, new=renames[old]))
            continue
        new = renames[old]      # (named by its entry, or by its wires as Hue cycle was)
        line, rings, wa, wb, add, spread = (free("line"), free("rings"), free("scale"),
                                            free("scale"), free("combine"), free("scale"))
        out_nodes += [entry(x) for x in (line, rings, wa, wb, add, spread)]
        # (the section's own wires go first, as a landing writes them —
        # `graphview._frame_order` — so an edit leaves the order as loaded;
        # a slot of Hue turn reads its effect's field, `graph._Build._fields`)
        band += [{"from": line, "to": f"{wa}.image"}, {"from": rings, "to": f"{wb}.image"},
                 {"from": wa, "to": f"{add}.image"}, {"from": wb, "to": f"{add}.field"},
                 {"from": add, "to": f"{spread}.image"},
                 {"from": spread, "to": f"{new}.turn", G.WIRE_DEPTH: HUE_TURN_DEPTH}]
        had = knobs.get(old, {})
        r = float(had.get("rings", HUE_CYCLE_DEFAULTS["rings"]))
        sp = float(had.get("spread", HUE_CYCLE_DEFAULTS["spread"]))
        pre = f"fx.{new}."
        values.update({pre + k: v for k, v in had.items() if k not in HUE_CYCLE_DEFAULTS})
        for name, kv in ((line, {"angle": 0.7853981633974483, "scale": 1.4142135623730951,
                                 "out": 0}),
                         (rings, {"scale": 2.0, "out": 0}),
                         (wa, {"mul": 1.0 - r, "offset": 0.0}), (wb, {"mul": r, "offset": 0.0}),
                         (add, {"how": 0}), (spread, {"mul": sp, "offset": 0.0})):
            values[f"fx.{name}.on"] = True
            values.update({f"fx.{name}.{k}": v for k, v in kv.items()})
        spread_to[old] = f"fx.{spread}.mul"
        for w in knob_fields:
            if w["to"].rpartition(".")[0] != new:
                continue
            d = float(w.get(G.WIRE_DEPTH, 1.0))
            if w["to"].endswith(".spread"):
                band.append({**w, "to": f"{spread}.mul", G.WIRE_DEPTH: d})
            else:       # Rings r weighs rings by r and the diagonal by 1 − r
                band.append({**w, "to": f"{wb}.mul", G.WIRE_DEPTH: d})
                band.append({**w, "to": f"{wa}.mul", G.WIRE_DEPTH: -d})
        notes.append(HUE_TURN_NOTE.format(old=old, new=new))
    out_wires = [*band, *out_wires]

    def param(pid: Any) -> Any:
        m = _HUE_PARAM.match(pid) if isinstance(pid, str) else None
        if m is None:
            return pid
        old = G.instance_name(HUE_CYCLE, int(m.group(1)) if m.group(1) else 1)
        if old not in renames:
            return pid
        if m.group(2) == "spread" and old in spread_to:
            return spread_to[old]
        return f"fx.{renames[old]}.{m.group(2)}"

    def row(r: Any, where: str) -> Any:
        if not isinstance(r, dict):
            return r
        t = r.get("target")
        m = _HUE_PARAM.match(t) if isinstance(t, str) else None
        if m is not None and m.group(2) in ("spread", "rings") and G.instance_name(
                HUE_CYCLE, int(m.group(1)) if m.group(1) else 1) not in spread_to:
            notes.append(HUE_RINGS_NOTE.format(row=f"{where} {r.get('source')} → {t}"))
            return None
        if m is not None and m.group(2) == "rings":
            notes.append(HUE_RINGS_NOTE.format(row=f"{where} {r.get('source')} → {t}"))
            return None
        out = {k: (param(v) if k in ("target", "scale", "source") else v) for k, v in r.items()}
        if m is not None and m.group(2) == "spread":
            op, v = r.get("op"), r.get("value", 1.0)       # (a row's default depth: 1)
            if op == "push" and isinstance(v, (int, float)):
                out["value"] = v / 2.0
            elif op == "set" and isinstance(v, (int, float)):
                out["value"] = v / 2.0 + 0.5
            elif op in ("abs", "abs14", "position"):
                # (a row that sets the knob's place, not a push about it: the
                # bands' × spans −4 … 4 where Spread spanned 0 … 4, and a row
                # holds no offset — kept, said; Devin on #509 for position)
                notes.append(HUE_ABS_NOTE.format(row=f"{where} {r.get('source')} → {t}"))
        return out

    def walk(v: Any) -> Any:
        if isinstance(v, str):
            if v.startswith("render:") and v[7:] in renames:
                return f"render:{renames[v[7:]]}"
            if v.startswith("key.") and _hue_old(v[4:]) in renames:     # (black is clear's knobs)
                return "key." + rename(v[4:])
            return param(rename(v)) if _HUE_PARAM.match(v) or _hue_old(v) else v
        if isinstance(v, dict):
            return {(walk(k) if isinstance(k, str) else k): walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    out_rest = {}
    for k, v in rest.items():
        if k == "values":
            out_rest[k] = {(walk(x) if x.startswith("key.") else x): y for x, y in values.items()}
        elif k in _ROW_LISTS and isinstance(v, list):
            out_rest[k] = [x for x in (row(r, k) for r in v) if x is not None]
        elif k == "macros" and isinstance(v, dict):
            out_rest[k] = walk(_hue_macros(v, _HUE_PARAM, spread_to, renames))
        else:
            out_rest[k] = walk(v)
    if "values" not in rest:
        out_rest["values"] = values
    out_ports = None if ports is None else [
        {**p, **({"to": rename(p["to"])} if isinstance(p.get("to"), str) else {}),
         **({"from": rename(p["from"])} if isinstance(p.get("from"), str) else {}),
         **({"was": rename(p["was"])} if isinstance(p.get("was"), str) else {})}
        if isinstance(p, dict) else p for p in ports]
    return out_nodes, out_wires, out_rest, out_ports, notes


def _hue_params(rest: dict) -> list[str]:
    """Every Hue cycle knob id `rest` mentions: its values' keys, and any text
    of its rows, macros and the rest (a row's target, a subscriber's base)."""
    found: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            if _HUE_PARAM.match(v):
                found.append(v)
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(k)
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(rest)
    return found


def _hue_macros(macros: dict, pattern: re.Pattern, spread_to: dict, renames: dict) -> dict:
    """The macros with a base subscriber on a Hue cycle's Spread moved onto its
    bands' × (`from` / `to` are norms: the same Spread is half way up plus
    half as far); every other mention renamed by the walk after."""
    out = {}
    for mid, m in macros.items():
        if not isinstance(m, dict) or not isinstance(m.get("subs"), list):
            out[mid] = m
            continue
        subs = []
        for sub in m["subs"]:
            got = pattern.match(sub.get("base")) if isinstance(sub, dict) and isinstance(
                sub.get("base"), str) else None
            if got is not None and got.group(2) == "spread":
                old = G.instance_name(HUE_CYCLE, int(got.group(1)) if got.group(1) else 1)
                if old in spread_to:
                    sub = {**sub, "base": spread_to[old],
                           **{k: sub[k] / 2.0 + 0.5 for k in ("from", "to")
                              if isinstance(sub.get(k), (int, float))}}
            subs.append(sub)
        out[mid] = {**m, "subs": subs}
    return out


def hue_turns(doc: dict) -> tuple[dict, list[str]]:
    """A whole loadable patch with every Hue cycle retired (`retire_hue_cycle`)
    — (the document, the notes); the document itself when it names none."""
    section = doc.get("graph") if isinstance(doc, dict) else None
    if not isinstance(section, dict) or not isinstance(section.get("nodes", []), list) \
            or not isinstance(section.get("wires", []), list):
        return doc, []
    rest = {k: v for k, v in doc.items() if k not in ("graph", "schema", "name")}
    nodes, wires, rest2, _, notes = retire_hue_cycle(
        list(section.get("nodes", [])), list(section.get("wires", [])), rest)
    if not notes:
        return doc, []
    out = {k: doc[k] for k in ("schema", "name") if k in doc}
    out.update(rest2)
    # (the section's other keys — black is clear's `keys` — name nodes too)
    others = {k: v for k, v in section.items() if k not in ("nodes", "wires")}
    _, _, others2, _, _ = retire_hue_cycle(list(section.get("nodes", [])),
                                           list(section.get("wires", [])), others)
    others2.pop("values", None)
    out["graph"] = {**others2, "nodes": nodes, "wires": wires}
    return out, notes


# ---------------------------------------------------------------- the look-back retired (plan 90)

# Plan 90 H2 (§10.2, §10.3; the owner's answers Q23–Q28): a look-back
# (`lookback`, `lookback.<n>`) is public parts — what it records through a
# Curve (only where its contrast is not 1, or a row drives it), a Fade (1 −
# darken) keyed black is clear (peak, linear, level 0, soft 1, keep colour: the
# old "brightness is coverage"), a Resize (512 on the long side), a Delay (depth
# = its echoes, every 1 / gap seconds in Hz, gap 0 every frame) read by a Trail
# (level = echo_mix, fade, lay over), cut by a Matte of its occluder (peak,
# linear, key ⅛, soft ⅛: min(4 · peak, 1)) and by its cover, each Cut's amount
# its occlude; where its picture went, the last of them. An echo pin
# `lookback.echo.<k>` is a Read at k − 1, nearest, of that delay — of a second
# delay, the same input, at depth k, past its echoes (Q25). Its knobs are the
# parts' (`dream.echo_mix` → `fx.trail.level` …); `dream.darken`, `contrast` and
# `res` stay the dream's until H3, a row on one copied onto the look-back's part
# too (Q26); a row on `dream.gap` is dropped, said (Q27). Keyed on the file, not
# a schema, as Hue cycle's retirement: run as the ladder's last step
LB_KEYS = ("echo_mix", "fade", "echoes", "gap", "darken", "contrast", "occlude", "res")
LB_GONE = ("echo_mix", "fade", "echoes", "gap", "occlude")       # dream's no more: retired
LB_SHARED = ("darken", "contrast", "res")                       # the dream's still (Q26)
LB_DEFAULTS: dict[str, Any] = {"echo_mix": 0.4, "fade": 0.2252, "echoes": 8, "gap": 0.033333,
                               "darken": 0.1, "contrast": 1.0, "occlude": 1.0, "res": 2}
LB_ECHOES = 32                   # dream.echoes ran 0 … 32
LB_DEPTH = (1, 64)               # a delay's depth (`view.DELAY_DEPTH`)
LB_CONTRAST = (0.5, 3.0)         # dream.contrast ran 0.5 … 3, linear
LB_HZ = (0.1, 120.0)             # a delay's Hz (`view.DELAY_HZ`)
LB_RESIZE = 5                    # `view.RESIZE_SIDES[5]`: 512 on the long side (Q24)
LB_MATTE = {"from": 3, "key": 0.125, "soft": 0.125, "ramp": 1, "invert": False, "feather": 0.0}
LB_KEY = {"measure": 0, "level": 0.0, "soft": 1.0, "keep": True, "feather": 0.0,
          "invert": False, "ramp": 1}
LOOKBACK_NOTE = ("{old} is public parts now (plan 90): {chain} — the same look, what it keeps "
                 "at 512 on the long side; save to keep it")
LB_ECHO_NOTE = "{pin} is {read} now (plan 90): a Read of {delay}, at {at}, nearest"
LB_GAP_NOTE = ("{row}: the look-back's gap is the delay's rate in Hz now ({delay}.hz), and a "
               "row on the gap has no straight line onto it — left out (plan 90)")
LB_RANGE_NOTE = ("{row}: {old} ran {was}, {new} runs {now} — the row is kept, its throw "
                 "spans the new range (plan 90)")
LB_NOWHERE_NOTE = "{row}: {old} drew nothing in this patch (plan 90): left out"
LB_NONE_NOTE = "{old} kept no echoes (echoes 0): its trail is off (plan 90)"
_LB_END = re.compile(r"^lookback(?:\.([2-9]|[1-9][0-9]+))?"
                     r"(?:\.(image|occluder|cover|capture)|\.echo\.([1-9][0-9]*))?$")
_LB_PARAM = re.compile(r"^dream\.(?:([2-9]|[1-9][0-9]+)\.)?(" + "|".join(LB_KEYS) + r")$")


def _lb_of(end: Any) -> tuple[str, str, int | None] | None:
    """A wire's end naming a look-back → (the look-back, its port or "",
    the echo pin's k or None): `lookback.2.echo.3` → ("lookback.2", "", 3)."""
    m = _LB_END.match(end) if isinstance(end, str) else None
    if m is None:
        return None
    name = "lookback" if m.group(1) is None else f"lookback.{m.group(1)}"
    return name, m.group(2) or "", int(m.group(3)) if m.group(3) else None


def _lb_param(pid: Any) -> tuple[str, str] | None:
    """A look-back knob → (its look-back, its key): `dream.2.fade` →
    ("lookback.2", "fade"), `dream.echo_mix` → ("lookback", "echo_mix")."""
    m = _LB_PARAM.match(pid) if isinstance(pid, str) else None
    if m is None:
        return None
    return ("lookback" if m.group(1) is None else f"lookback.{m.group(1)}"), m.group(2)


def _lb_prefix(lb: str) -> str:
    return "dream." if lb == "lookback" else f"dream.{lb.partition('.')[2]}."


def _num(v: Any, default: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return float(default)
    return x if math.isfinite(x) else float(default)


def _norm(v: float, lo: float, hi: float) -> float:
    return min(max((v - lo) / (hi - lo), 0.0), 1.0)


def retire_lookbacks(nodes: list, wires: list, rest: dict, ports: list | None = None,
                     keys: list | None = None
                     ) -> tuple[list, list, dict, list | None, list | None, list[str]]:
    """A section's `nodes` and `wires`, the document's other keys (`rest`),
    a fragment's `ports` and the section's `keys` (black is clear's), with
    every look-back made public parts (module notes above) — (nodes, wires,
    rest, ports, keys, notes). Pure: the inputs are untouched, and handed
    back as they are when no look-back is named. The retired knobs
    (`LB_GONE`, `dream.<n>.*`) of a patch with no look-back drew nothing:
    their values go quietly, a row on one is left out, said."""
    olds: list[str] = []
    for e in nodes:
        if isinstance(e, dict) and e.get("kind") == "lookback":
            n = e.get("instance", 1)
            olds.append("lookback" if n in (1, None) else f"lookback.{n}")
    for w in wires:
        if isinstance(w, dict):
            for end in (w.get("from"), w.get("to")):
                got = _lb_of(end)
                if got is not None and got[0] not in olds:
                    olds.append(got[0])
    for p in ports or []:
        if isinstance(p, dict):
            for end in (p.get("from"), p.get("to")):
                got = _lb_of(end)
                if got is not None and got[0] not in olds:
                    olds.append(got[0])
    olds.sort(key=lambda n: int(n.partition(".")[2] or 1))
    values = dict(rest.get("values") or {}) if isinstance(rest.get("values"), dict) else {}
    named = [k for k in values if _lb_param(k) is not None
             and (_lb_param(k)[1] in LB_GONE or _lb_param(k)[0] != "lookback")]
    row_named = any(_lb_param(r.get("target")) is not None
                    and (_lb_param(r["target"])[1] in LB_GONE
                         or _lb_param(r["target"])[0] != "lookback")
                    for key in _ROW_LISTS for r in (rest.get(key) or [])
                    if isinstance(r, dict))
    if not olds and not named and not row_named:
        return nodes, wires, rest, ports, keys, []
    taken: set[str] = set()
    for e in nodes:
        if not isinstance(e, dict):
            continue
        n = e.get("instance", 1)
        n = n if isinstance(n, int) else 1
        if isinstance(e.get("file"), str):
            taken.add(G.instance_name(e["file"], n))
        elif isinstance(e.get("kind"), str):
            taken.add(G.instance_name(e["kind"], n))
    for w in wires:
        if isinstance(w, dict):
            for end in (w.get("from"), w.get("to")):
                if isinstance(end, str) and _lb_of(end) is None:
                    taken.add(_effect_base(end))

    def free(kind: str) -> str:
        n = 1
        while G.instance_name(kind, n) in taken:
            n += 1
        name = G.instance_name(kind, n)
        taken.add(name)
        return name

    def entry(kind: str, name: str, effect: bool) -> dict:
        _, n = G.split_instance(name)
        out: dict[str, Any] = {"kind": "effect", "file": kind} if effect else {"kind": kind}
        if n != 1:
            out["instance"] = n
        return out

    driven: set[str] = set()
    for key in _ROW_LISTS:
        for r in rest.get(key) or []:
            if isinstance(r, dict) and isinstance(r.get("target"), str):
                driven.add(r["target"])
    for m in (rest.get("macros") or {}).values() if isinstance(rest.get("macros"), dict) else ():
        for s in (m.get("subs") or []) if isinstance(m, dict) else []:
            if isinstance(s, dict) and isinstance(s.get("base"), str):
                driven.add(s["base"])

    notes: list[str] = []
    out_nodes = [e for e in nodes if not (isinstance(e, dict) and e.get("kind") == "lookback")]
    out_keys = list(keys) if keys is not None else None
    new_wires: list[dict] = []
    ends: dict[str, str] = {}          # a look-back → the part its picture is now
    heads: dict[str, dict[str, str]] = {}   # a look-back's port → the part's port
    pins: dict[tuple[str, int], str] = {}   # (look-back, k) → its Read
    parts: dict[str, dict[str, Any]] = {}   # a look-back → its parts, by role
    for old in olds:
        pre = _lb_prefix(old)
        v = {k: values.get(pre + k, LB_DEFAULTS[k]) for k in LB_KEYS}

        def into(port: str, old: str = old) -> Any:
            return next((w.get("from") for w in wires if isinstance(w, dict)
                         and _lb_of(w.get("to")) == (old, port, None)), None)
        src, occ, cover = into("image") or into("capture"), into("occluder"), into("cover")
        read_out = any(isinstance(w, dict) and _lb_of(w.get("from")) == (old, "", None)
                       for w in wires) or any(
            isinstance(p, dict) and _lb_of(p.get("from")) == (old, "", None) for p in ports or [])
        ks = sorted({_lb_of(w.get("from"))[2] for w in wires if isinstance(w, dict)
                     and _lb_of(w.get("from")) is not None and _lb_of(w.get("from"))[0] == old
                     and _lb_of(w.get("from"))[2] is not None})
        echoes = int(round(_num(v["echoes"], LB_DEFAULTS["echoes"])))
        depth = min(max(echoes, LB_DEPTH[0]), LB_DEPTH[1])
        contrast = _num(v["contrast"], 1.0)
        curve_on = contrast != 1.0 or pre + "contrast" in driven
        role: dict[str, Any] = {}
        chain: list[str] = []
        if curve_on:
            role["curve"] = free("curve")
            out_nodes.append(entry("curve", role["curve"], True))
            chain.append(f"Curve ({role['curve']})")
        role["fade"] = free("fade")
        role["resize"] = free("resize")
        role["delay"] = free("delay")
        out_nodes += [entry("fade", role["fade"], True), entry("resize", role["resize"], False),
                      entry("delay", role["delay"], False)]
        chain += [f"Fade, keyed ({role['fade']})", f"Resize ({role['resize']})",
                  f"Delay ({role['delay']})"]
        if out_keys is None:
            out_keys = []
        out_keys.append(role["fade"])
        first = role.get("curve", role["fade"])
        heads[old] = {"image": f"{first}.image", "capture": f"{first}.image"}
        wl: list[dict] = []
        if src is not None:
            wl.append(_w(src, f"{first}.image"))
        if curve_on:
            wl.append(_w(role["curve"], f"{role['fade']}.image"))
        wl += [_w(role["fade"], f"{role['resize']}.image"),
               _w(role["resize"], f"{role['delay']}.image")]
        end = None
        if read_out:
            role["trail"] = free("trail")
            out_nodes.append(entry("trail", role["trail"], True))
            chain.append(f"Trail ({role['trail']})")
            wl.append(_w(role["delay"], f"{role['trail']}.stack"))
            end = role["trail"]
            if occ is not None:
                role["matte"], role["cut"] = free("matte"), free("cut")
                out_nodes += [entry("matte", role["matte"], False),
                              entry("cut", role["cut"], False)]
                chain += [f"Cut ({role['cut']}) by a Matte of its occluder ({role['matte']})"]
                wl += [_w(end, f"{role['cut']}.image"), _w(occ, f"{role['matte']}.image"),
                       _w(role["matte"], f"{role['cut']}.mask")]
                heads[old]["occluder"] = f"{role['matte']}.image"
                end = role["cut"]
            if cover is not None or any(isinstance(p, dict) and _lb_of(p.get("to")) == (
                    old, "cover", None) for p in ports or []):
                role["cover_cut"] = free("cut")
                out_nodes.append(entry("cut", role["cover_cut"], False))
                chain.append(f"Cut ({role['cover_cut']}) by its cover")
                wl.append(_w(end, f"{role['cover_cut']}.image"))
                if cover is not None:
                    wl.append(_w(cover, f"{role['cover_cut']}.mask"))
                heads[old]["cover"] = f"{role['cover_cut']}.mask"
                end = role["cover_cut"]
            ends[old] = end
        deep = [k for k in ks if k > depth]
        if deep:
            role["deep"] = free("delay")
            out_nodes.append(entry("delay", role["deep"], False))
            wl.append(_w(role["resize"], f"{role['deep']}.image"))
        for k in ks:
            read = free("read")
            out_nodes.append(entry("read", read, True))
            maker = role["deep"] if k > depth else role["delay"]
            wl.append(_w(maker, f"{read}.stack"))
            pins[(old, k)] = read
            values[f"fx.{read}.on"] = True
            values[f"fx.{read}.at"] = float(k - 1)
            values[f"fx.{read}.between"] = 1
            notes.append(LB_ECHO_NOTE.format(pin=f"{old}.echo.{k}", read=read, delay=maker,
                                             at=k - 1))
        new_wires += wl
        # (its values: the parts', each from the look-back's own)
        for k in LB_KEYS:
            if k in LB_GONE or old != "lookback":
                values.pop(pre + k, None)
        darken = _num(v["darken"], LB_DEFAULTS["darken"])
        if curve_on:
            values[f"fx.{role['curve']}.on"] = True
            values[f"fx.{role['curve']}.shape"] = min(max(
                math.log(max(contrast, 1e-6)) / math.log(4.0), -1.0), 1.0)
        values[f"fx.{role['fade']}.on"] = True
        values[f"fx.{role['fade']}.level"] = min(max(1.0 - darken, 0.0), 1.0)
        values.update({f"key.{role['fade']}.{k}": x for k, x in LB_KEY.items()})
        values.update({f"{role['resize']}.size": LB_RESIZE, f"{role['resize']}.aspect": 0,
                       f"{role['resize']}.fit": 0, f"{role['resize']}.filter": 0})
        gap = _num(v["gap"], LB_DEFAULTS["gap"])
        for d, dd in ((role["delay"], depth), (role.get("deep"), max(deep, default=0))):
            if d is None:
                continue
            values[f"{d}.depth"] = dd
            if gap <= 0.0:
                values.update({f"{d}.every": 0, f"{d}.frames": 1})
            else:
                values.update({f"{d}.every": 1, f"{d}.frames": 1,
                               f"{d}.hz": round(min(max(1.0 / gap, LB_HZ[0]), LB_HZ[1]), 3)})
        if "trail" in role:
            t = role["trail"]
            values[f"fx.{t}.on"] = echoes > 0
            values[f"fx.{t}.level"] = _num(v["echo_mix"], LB_DEFAULTS["echo_mix"])
            values[f"fx.{t}.fade"] = _num(v["fade"], LB_DEFAULTS["fade"])
            values[f"fx.{t}.lay"] = 0
            if echoes <= 0:
                notes.append(LB_NONE_NOTE.format(old=old))
        occlude = min(max(_num(v["occlude"], LB_DEFAULTS["occlude"]), 0.0), 1.0)
        if "matte" in role:
            values.update({f"{role['matte']}.{k}": x for k, x in LB_MATTE.items()})
        for c in (role.get("cut"), role.get("cover_cut")):
            if c is not None:
                values.update({f"{c}.amount": occlude, f"{c}.invert": False})
        parts[old] = role
        notes.append(LOOKBACK_NOTE.format(old=old, chain=" → ".join(chain)))
    # every other look-back knob (a patch with none, or `dream.<n>.*` of none drawn)
    for k in list(values):
        got = _lb_param(k)
        if got is not None and (got[1] in LB_GONE or got[0] != "lookback"):
            del values[k]

    out_wires: list[Any] = []
    for w in wires:
        if not isinstance(w, dict):
            out_wires.append(w)
            continue
        f, t = _lb_of(w.get("from")), _lb_of(w.get("to"))
        if t is not None:
            continue                     # (into a look-back: its parts' wires above)
        if f is not None:
            if f[2] is not None:
                w = {**w, "from": pins[(f[0], f[2])]}
            elif f[0] in ends:
                w = {**w, "from": ends[f[0]]}
            else:
                continue
        out_wires.append(w)
    out_wires = [*new_wires, *out_wires]

    def retarget(pid: str) -> list[str] | None:
        """Where a row on look-back knob `pid` goes: the ids, [] dropped, None not one."""
        got = _lb_param(pid)
        if got is None:
            return None
        lb, k = got
        role = parts.get(lb)
        keep = [pid] if lb == "lookback" and k in LB_SHARED else []
        if role is None:
            return keep
        new = {"echo_mix": [f"fx.{role['trail']}.level"] if "trail" in role else [],
               "fade": [f"fx.{role['trail']}.fade"] if "trail" in role else [],
               "echoes": [f"{role['delay']}.depth"],
               "gap": [],
               "darken": [f"fx.{role['fade']}.level"],
               "contrast": [f"fx.{role['curve']}.shape"] if "curve" in role else [],
               "occlude": [f"{c}.amount" for c in (role.get("cut"), role.get("cover_cut"))
                           if c is not None],
               "res": []}[k]
        return keep + new

    def base_of(pid: str, k: str) -> float:
        lb, _ = _lb_param(pid)
        return _num((rest.get("values") or {}).get(_lb_prefix(lb) + k, LB_DEFAULTS[k])
                    if isinstance(rest.get("values"), dict) else LB_DEFAULTS[k], LB_DEFAULTS[k])

    def moved(r: dict, pid: str, new: str, where: str) -> dict | None:
        """Row `r` on look-back knob `pid` as one on `new`, its reach kept."""
        _, k = _lb_param(pid)
        out = {**r, "target": new}
        op, val = r.get("op"), r.get("value", 1.0)
        label = f"{where} {r.get('source')} → {pid}"
        num = isinstance(val, (int, float)) and not isinstance(val, bool)
        if k == "darken" and num:
            if op == "push":
                out["value"] = -val
            elif op == "set":
                out["value"] = 1.0 - val
        elif k == "echoes" and num:
            if op == "push":
                out["value"] = round(val * LB_ECHOES / (LB_DEPTH[1] - LB_DEPTH[0]), 6)
            elif op == "set":
                out["value"] = round(_norm(val * LB_ECHOES, *LB_DEPTH), 6)
        elif k == "contrast" and num:
            c0 = min(max(base_of(pid, "contrast"), LB_CONTRAST[0]), LB_CONTRAST[1])
            span = LB_CONTRAST[1] - LB_CONTRAST[0]
            if op == "push":     # (about the file's contrast: d shape = d c / (c ln 4))
                out["value"] = round(val * span / (c0 * math.log(4.0)) / 2.0, 6)
            elif op == "set":
                c = LB_CONTRAST[0] + val * span
                out["value"] = round((math.log(c) / math.log(4.0) + 1.0) / 2.0, 6)
        if op in ("abs", "abs14", "position") and k in ("darken", "echoes", "contrast"):
            was = {"darken": "0 … 1", "echoes": "0 … 32", "contrast": "0.5 … 3"}[k]
            now = {"darken": "1 … 0 (its level)", "echoes": "1 … 64",
                   "contrast": "−1 … 1 (log₄)"}[k]
            notes.append(LB_RANGE_NOTE.format(row=label, old=pid, was=was, new=new, now=now))
        return out

    def row(r: Any, where: str) -> list:
        if not isinstance(r, dict):
            return [r]
        t = r.get("target")
        to = retarget(t) if isinstance(t, str) else None
        if to is None:
            return [r]
        label = f"{where} {r.get('source')} → {t}"
        _, k = _lb_param(t)
        if k == "gap" and _lb_param(t)[0] in parts:
            notes.append(LB_GAP_NOTE.format(row=label, delay=parts[_lb_param(t)[0]]["delay"]))
        elif not to:
            notes.append(LB_NOWHERE_NOTE.format(row=label, old=t))
        return [r if new == t else moved(r, t, new, where) for new in to]

    def macros(ms: dict) -> dict:
        out = {}
        for mid, m in ms.items():
            if not isinstance(m, dict) or not isinstance(m.get("subs"), list):
                out[mid] = m
                continue
            subs = []
            for s in m["subs"]:
                to = retarget(s.get("base")) if isinstance(s, dict) else None
                if to is None:
                    subs.append(s)
                    continue
                if not to:
                    notes.append(LB_NOWHERE_NOTE.format(row=f"macros {mid}", old=s["base"]))
                for new in to:
                    if new == s["base"]:
                        subs.append(s)
                        continue
                    _, k = _lb_param(s["base"])
                    ns = {**s, "base": new}
                    for end in ("from", "to"):
                        x = s.get(end, 0.0 if end == "from" else 1.0)
                        if not isinstance(x, (int, float)):
                            continue
                        if k == "darken":
                            ns[end] = 1.0 - x
                        elif k == "echoes":
                            ns[end] = round(_norm(x * LB_ECHOES, *LB_DEPTH), 6)
                        elif k == "contrast":
                            c = LB_CONTRAST[0] + x * (LB_CONTRAST[1] - LB_CONTRAST[0])
                            ns[end] = round((math.log(c) / math.log(4.0) + 1.0) / 2.0, 6)
                    subs.append(ns)
            out[mid] = {**m, "subs": subs}
        return out

    renames = {f"render:{old}": f"render:{parts[old]['delay']}" for old in parts}

    def walk(v: Any) -> Any:
        if isinstance(v, str):
            return renames.get(v, v)
        if isinstance(v, dict):
            return {(walk(k) if isinstance(k, str) else k): walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    out_rest: dict[str, Any] = {}
    for k, v in rest.items():
        if k == "values":
            out_rest[k] = values
        elif k in _ROW_LISTS and isinstance(v, list):
            out_rest[k] = [x for r in v for x in row(r, k)]
        elif k == "macros" and isinstance(v, dict):
            out_rest[k] = walk(macros(v))
        else:
            out_rest[k] = walk(v)
    if "values" not in rest and values:
        out_rest["values"] = values
    if out_keys is not None:
        out_keys = sorted({x if x not in ends else ends[x] for x in out_keys
                           if isinstance(x, str) and _lb_of(x) is None or x in ends})
    out_ports = None
    if ports is not None:
        out_ports = []
        for p in ports:
            if not isinstance(p, dict):
                out_ports.append(p)
                continue
            q = dict(p)
            got = _lb_of(p.get("to"))
            if got is not None:
                head = heads.get(got[0], {}).get(got[1])
                if head is None:
                    continue
                q["to"] = head
            got = _lb_of(p.get("from"))
            if got is not None:
                src = pins.get((got[0], got[2])) if got[2] is not None else ends.get(got[0])
                if src is None:
                    continue
                q["from"] = src
            out_ports.append(q)
    if not notes and not olds:
        notes.append("the look-back's retired knobs dropped: no look-back drew them (plan 90)")
    return out_nodes, out_wires, out_rest, out_ports, out_keys, notes


def lookbacks(doc: dict) -> tuple[dict, list[str]]:
    """A whole loadable patch with every look-back made public parts
    (`retire_lookbacks`) — (the document, the notes); the document itself
    when it names none."""
    section = doc.get("graph") if isinstance(doc, dict) else None
    if not isinstance(section, dict) or not isinstance(section.get("nodes", []), list) \
            or not isinstance(section.get("wires", []), list):
        return doc, []
    rest = {k: v for k, v in doc.items() if k not in ("graph", "schema", "name")}
    keys = section.get(G.KEYS_KEY)
    nodes, wires, rest2, _, keys2, notes = retire_lookbacks(
        list(section.get("nodes", [])), list(section.get("wires", [])), rest,
        keys=list(keys) if isinstance(keys, list) else None)
    if not notes:
        return doc, []
    out = {k: doc[k] for k in ("schema", "name") if k in doc}
    out.update(rest2)
    others = {k: v for k, v in section.items() if k not in ("nodes", "wires", G.KEYS_KEY)}
    graph = {**others, "nodes": nodes, "wires": wires}
    if keys2:
        graph[G.KEYS_KEY] = keys2
    out["graph"] = graph
    return out, notes


# ---------------------------------------------------------------- the one ladder (plan 50)

# what a load says of a file naming a desk template (retired, plan 44 D3;
# `loadable.TEMPLATE_RETIRED` is this)
TEMPLATE_RETIRED = ("desk template {name!r}: desk templates are retired (plan 44 D3) — "
                    "this patch's own desk rows only")


@dataclass(frozen=True)
class Forward:
    """What `forward` made of a preset: the document in today's words, the
    notes a load says (a retired desk template named), the migration's own
    notes (an effect left out of the run: `left_out_of`), the line saying an
    old file was migrated ("" when it was `/7` or newer), and the look ids
    the open show handed on to a file before `/10` (`ten`; a leftover the
    graph does not declare is dropped quietly by the load)."""

    doc: dict
    notes: tuple[str, ...] = ()
    migrate_notes: tuple[str, ...] = ()
    migrated: str = ""
    from_show: frozenset[str] = frozenset()


def eleven(doc: dict) -> dict:
    """A `/10` as its `/11` (plan 57 §7): the kind's new word, and a pair route's poles in
    north, south, east and west (a load drops a `pad:` or `hat:` route, so only a pair's names
    a pole). A copy."""
    out = {**doc, "schema": ELEVEN_SCHEMA}
    routes = doc.get("routes")
    if isinstance(routes, list):
        out["routes"] = [{**r, "source": nsew(r["source"])}
                         if isinstance(r, dict) and isinstance(r.get("source"), str) else r
                         for r in routes]
    return out


def forward(doc: dict, specs: Specs, *, eye: dict | None = None, camera_at: Any = None,
            look: dict | None = None, cuts: Any = None) -> Forward:
    """The one ladder for a whole loadable patch (plan 50; the steps a load runs,
    in order, each only for a file older than it): before `/7` the one-way
    migration (`seven`, said), before `/9` the eye and the camera's GRAPH
    place the open show held (`nine`), before `/10` the look made whole
    (`ten`: the show's hands' and clouds' looks and its bus cuts, the
    module labels and the desk template's name dropped — the template
    said), before `/11` the kind's new word (`eleven`), and — first, before
    any step reads the section — before `/12` its copies made slots of
    their effects (`twelve`, plan 89; said when there were any); last, at
    any version, a Hue cycle made Hue turn and its bands' field nodes
    (`hue_turns`, plan 67; said). A
    fragment's ladder is `patches.forward`; the two are the one reader of
    the one shape (`patches.shape_of` says which a file is)."""
    notes: list[str] = []
    migrate_notes: list[str] = []
    migrated = ""
    from_show: set[str] = set()
    version = schema_version(doc)
    specs = {**RETIRED_SPECS, **specs}      # (plan 67: Hue cycle, retired below)
    if version is None or version < TWELVE:
        # plan 89: copies are slots before anything reads the section (a
        # `/6` wired frame may hold one; the steps below read slots alone)
        was = doc
        doc, slot_notes = twelve(doc)
        migrate_notes += slot_notes
        if doc is not was:
            migrated = SLOTS_MIGRATED_NOTE.format(old=str(doc.get("schema")),
                                                  new=TWELVE_SCHEMA)
    if version is None or version < SEVEN:
        old = str(doc.get("schema"))
        doc, seven_notes = seven(doc, specs)
        migrate_notes += seven_notes
        migrated = MIGRATED_NOTE.format(old=old, new=TWELVE_SCHEMA)
    if version is None or version < NINE:
        doc = nine(doc, eye, camera_at)
    if version is None or version < TEN:
        if doc.get("desk_template"):
            notes.append(TEMPLATE_RETIRED.format(name=str(doc["desk_template"])))
        had = set(dict(doc.get("values") or {})) if isinstance(doc.get("values"), dict) \
            else set()
        doc = ten(doc, look, cuts)
        from_show = set(dict(doc.get("values") or {})) - had \
            if isinstance(doc.get("values"), dict) else set()
    if version is None or version < ELEVEN:
        doc = eleven(doc)
    if version is None or version < TWELVE:
        doc = {**doc, "schema": TWELVE_SCHEMA}
    # plan 67: Hue cycle retired, whatever the version (keyed on the file)
    doc, hue_notes = hue_turns(doc)
    migrate_notes += hue_notes
    # plan 90 (H2): the look-back made public parts, whatever the version
    doc, lb_notes = lookbacks(doc)
    migrate_notes += lb_notes
    return Forward(doc, tuple(notes), tuple(migrate_notes), migrated, frozenset(from_show))
