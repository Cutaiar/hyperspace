"""The preset — one file that holds everything a performance moment is
(plan 13 D1, §2.1): ``hyperspace.preset/2``.

  {"schema": "hyperspace.preset/2", "name": "TRIP", "note": "…",
   "values": {id: base, …},            the performance part (params.PARTS)
   "routes": [row, …],                 the performer rows (routing.Binding)
   "desk":   [row, …],                 the APC40's preset layer (routing.Binding)
   "macros": {"macro.1": {…}, …},      the macros' labels and subscribers
   "modules": {"fx": "trip", …}}       module-preset labels (D3)

(plan 24 C3: a file may also name a desk template, ``"desk_template":
"<name>"`` before ``desk``, and then ``desk`` holds only its overrides —
"desk templates" below.)

(plan 32 S: a ``media`` section holds the channels' bins:
``{"channels": {"a": ["shared:loops/tunnel.mp4", null, …], …}}``.)

**The schema a save writes** (row 394, the owner's decision of
2026-10-25, superseding D1's ladder, R10 and R15): always the newest,
``hyperspace.preset/7`` (`WIRED_SCHEMA`), in today's words — the wired
frame (plan 35) that says everything (plan 36 W3: every edge a wire, the
hands entries and `laid` written, effects only where the section names
them), today's node ids and canvas ids, every value the registry holds
(the media family, the envelopes and the sequencer), no retired id
written back. Both Macs run the same build, so nothing is written for an
older one. A ``/7`` is read as it is: nothing is added to it, and one
with no graph section is black. Every older schema (`VERSIONS`) is read
only through the one-way migration to ``/7`` (`graphmigrate.seven`), with
a note: ``/2`` is the format above, ``/3`` adds the envelopes and the
sequencer (plan 31), ``/4`` media (plan 32), ``/5`` the free graph (plan
33), ``/6`` the wired frame (plan 35); a re-save is ``/7``.
tools/migrate_library.py rewrites a library's presets that way, once.

One file per preset, ``<root>/presets/<slug>.json``: the factory ones in
``hyperspace/library/presets/``, the user's in ``<home>/presets/``
shadowing by name. `Presets` registers the folder with the library as a
**document kind** (`Library.kind`), so listing, shadowing, load / save
as / delete, the dirty dot and the file watch are the library's, and
the one preset strip (ui_presets.strip over ``presets``) drives it. The
bank (F1–F8, the APC40's clip row 1) names these files; the project
holds the bank (library.Project, ``hyperspace.project/2``). Since plan 13
WP5 it is the only kind: the routing presets are presets now.

A load is a scene-setter (docs/ARCHITECTURE.md §3): it writes bases and
replaces rows, never an offset. In order (plan 13 §5):

1. note what the file names that a preset may not: a session param
   ("`tempo.bpm` is the session's, ignored"), an id nobody has, a
   ``routes`` row that is not a performer row or that aims at a param
   that is not modulatable (dropped), a second performer on one target
   (the referee's, below);
2. land the values: **every** persisted param of every performance group
   gets the file's value or its group default (`Library.resolved`: the
   group's default module preset over the build values), in registry
   order, in one go (D2). A session param is never touched, and the
   rotation phases (not persisted) are left spinning;
3. replace every performer row with ``routes`` (`Bindings.set_routes`;
   the referee is first-wins, the rest in ``table.dropped`` for the
   ROUTING page);
4. replace the desk's preset layer with ``desk`` (`Bindings.set_desk`: a
   row on an invariant control is dropped and its note joins step 1's;
   the desk drops to the preset layer, D4, and the MIDI adapter redraws
   every ring and LED with the faders' catch cleared). A file with **no**
   ``desk`` key gets the factory preset layer (`routing.factory_desk`'s
   preset rows — a fresh preset, plan 13 §3.2); ``"desk": []`` is an
   empty preset layer, every preset control dark (D8);
5. replace the macros' labels and subscribers with ``macros``
   (`Bindings.set_macros`: a base subscriber on anything but a
   performance param — a session one, D9 — is dropped and its note joins
   step 1's) and land the base subscribers at once from the macros' bases
   just landed (`Router.follow_macros(force=True)`). The macro is the
   scene-setter of record: a param a base subscriber names ends at the
   subscriber's value even when ``values`` names it too;
6. record each performance group's ``modules`` label as its current
   module preset, clean against the values just landed — a label only,
   never a chain-load of the module preset (D3); a group the file does
   not name shows none;
7. the notes from step 1 are kept in ``notes`` and summed up in
   ``Library.warning`` for the panel.

A save (`document`) writes the performance snapshot, every performer row
(disabled ones too), the table's preset-layer rows (`Bindings.desk`, a
row's ``layer`` left out: every desk row is the preset's), the table's
macros (`Bindings.macros_doc`) and the performance groups' current
module labels. The dirty dot (`signature`) covers all of it, so a Learn,
an Unbind or a ROUTING-page edit — which change the table and write no
file — shows as the loaded preset edited; only a save (⇧F, the strip's
save / as…) writes it.

The factory presets' sources are generated (`python -m hyperspace.preset
DIR`, `write_factory`, pinned by tests/test_presets.py against
tests/fixtures/factory-sources/presets/): the code below holds
the generator's inputs — the house presets' routes (the lane rows),
plan 12's five party presets' routes and their desk blocks, and whole the five that were routing presets (``legacy6``,
``lfo-breathe``, ``hands-fx``, ``hands-pinch``, ``hands-play``) and
plan 18's ``hands-orbit`` and plan 31's ``seq-demo`` (`FACTORY_PRESETS`); every factory preset's ``desk`` is the factory
preset layer unless its entry says otherwise. The house presets' and the
party presets' values are data in their files.

Those sources stay in the schema they were made in (``/2``, seq-demo
``/3``: `factory_schema`). Plan 36 T3 (D5): the factory files themselves
are their ``/7`` — each source through tools/migrate_library.py (``--to
hyperspace/library/presets``), a fixed point a load and a save leave as
it is.

The first launch of this build migrates the home folder once
(`migrate_home`, plan 13 §6): see "the migration" below.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from . import apc40, graphmigrate, graphview, modifiers, routing, tapers, undo
from .bands import BANDS
from .fx import declare as declare_fx
from .ghost import GhostState
from .ghost import prefix as ghost_prefix
from .ghost import register as declare_ghost
from .graph import EMPTY, FRAME_KEY, WIRED_FRAME, GraphError, GraphSpec, Wiring, read_graph
from .lfo import SHAPES, SYNCS
from .library import (
    DESK_SCHEMA,
    F_KEYS,
    FACTORY,
    HOUSE_PROJECT,
    MINE_PROJECT,
    PERFORMANCE_SCHEMA,
    PRESETS,
    PROJECT_SCHEMA,
    PROJECT_SUFFIX,
    PROJECT_V1,
    PROJECTS,
    SLOTS,
    LibraryError,
    _module_values,
    _write_text,
    bank_doc,
    read_positions,
    slug,
)
from .lookback import (
    LEGACY,
    fade_depth,
    fade_of_decay,
    gap_of_every,
    migrate_row,
    migrate_values,
)
from .media import channels as media_channels
from .modifiers import Modifier
from .palettecompat import palette_slice
from .params import (  # noqa: F401 — pan_world, UNITS…: re-exported, preset.* names
    PAN_IDS,
    PERFORMANCE_GROUPS,
    PLANES,
    RESIZE_GROUP,
    SESSION_GROUPS,
    SWITCH_GROUP,
    UNITS,
    UNITS_KEY,
    declare_lookbacks,
    declare_resizes,
    declare_switches,
    is_instance_id,
    is_lookback_id,
    is_lookback_knob,
    is_resize_id,
    is_switch_id,
    pan_world,
    part_of,
)
from .routing import MOD_OPS, Binding, Macro, Sub, is_continuous

SCHEMA = PERFORMANCE_SCHEMA
# the schemas a load reads (each migrated on load; row 394: a save writes
# `WIRED_SCHEMA` only). /3 is /2 plus the envelopes and the sequencer (plan
# 31 P), /4 /3 plus media (plan 32 S, D1), /5 /4 plus the free graph (plan
# 33 M), /6 /5 with the wired frame in the new ids (plan 35, row 385)
SCHEMA_V3 = f"{SCHEMA.rpartition('/')[0]}/3"
MEDIA_SCHEMA = f"{SCHEMA.rpartition('/')[0]}/4"
FREE_SCHEMA = graphmigrate.FREE_SCHEMA
WIRED_SCHEMA = graphmigrate.WIRED_SCHEMA
VERSIONS = (2, 3, 4, 5, 6, 7)
# the registry groups (and lane schemes) a /2 file never names
V3_GROUPS = ("env", "seq")
# the preset keys a bank writes only off its default (modbank, plan 31 B)
V3_KEYS = ("lfos", "envs")
GROUP = PRESETS                   # the library folder, and the strip's group
# plan 35 T7 (row 387): the new preset — what the strip's `new` chip starts,
# named until it is saved, and what it says
UNTITLED_PRESET = "untitled"
NEW_SAID = "new preset: factory values, shape → scene → All outputs — a shape on every window"
# plan 36 T3 (W3): a `/7` with no graph section, or an empty one — the strip says so
NO_GRAPH_SAID = "no graph: nothing is wired — black until something is wired to an output"
# … and one whose section is not a wired frame (no `"frame": "wired"`)
UNWIRED_SAID = ("graph: a /7 section is a wired frame (\"frame\": \"wired\"); this one is "
                "not read — black")

# plan 32 S (row 337): the media section
MEDIA_KEY = "media"
BMP_PREFIX = "view.bmp_"          # the one bitmap file's params, gone in plan 32


FACTORY_DIR = FACTORY / GROUP
# plan 36 T3 (D5): what the factory presets are made from — the `/2` (seq-demo
# `/3`) sources the generator writes (`write_factory`), each migrated to the
# `/7` in FACTORY_DIR by tools/migrate_library.py (`--to`). A development
# folder beside the tests (migration inputs), never read by the app
FACTORY_SOURCES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / \
    "factory-sources" / GROUP


def _names_v3(x) -> bool:
    """Whether a routes / modifiers / macros section names an ``env``/``seq``
    lane (``env:0``) or param (``seq.1.3``) anywhere — labels and notes
    aside."""
    if isinstance(x, str):
        return x.startswith(tuple(f"{g}{c}" for g in V3_GROUPS for c in ":."))
    if isinstance(x, dict):
        return any(_names_v3(v) for k, v in x.items() if k not in ("label", "name", "note"))
    if isinstance(x, (list, tuple)):
        return any(_names_v3(v) for v in x)
    return False


def factory_schema(doc: dict) -> str:
    """The schema a generated factory preset is written in (`generated`):
    ``hyperspace.preset/3`` when it carries a bank's membership key, an
    ``env.*``/``seq.*`` value, or a route, modifier or macro on an envelope
    or the sequencer (plan 31's seq-demo), else ``hyperspace.preset/2``.

    Only the factory's generator asks. The factory files are the build's
    own read-only stock — never a save, never in the shared library — read
    through the same migration as any old file on every load, so they stay
    the files they were made as. A performance preset's save always writes
    `WIRED_SCHEMA` (row 394: the owner's decision of 2026-10-25, every
    machine on the newest schema; `Presets.document`)."""
    if any(k in doc for k in V3_KEYS):
        return SCHEMA_V3
    if any(str(k).startswith(tuple(f"{g}." for g in V3_GROUPS))
           for k in (doc.get("values") or {})):
        return SCHEMA_V3
    if any(_names_v3(doc.get(k)) for k in ("routes", MODIFIERS_KEY, "macros")):
        return SCHEMA_V3
    return SCHEMA


def desk_json(rows) -> list[dict]:
    """Preset-layer rows as a preset's ``desk``: each row's JSON without
    its ``layer`` — in a preset every desk row is the preset layer's
    (`Bindings.set_desk` forces it on the way back in)."""
    out = []
    for b in rows:
        d = b.to_json()
        d.pop("layer", None)
        out.append(d)
    return out


def fresh_desk(profile: str = "apc40") -> list[Binding]:
    """A fresh preset's desk: the factory map's preset layer (plan 13 §3.2)
    — what a file with no ``desk`` key gets, and what a factory preset's
    desk is once loaded (`file_desk` less the rows a load drops). It holds
    no track fader (plan 24 C2: the faders are a preset's own targets, with
    no inherited default), so a fresh preset leaves S1–S8 dark; a fader row
    a preset's desk holds (`track_fader`) loads, saves and lights like a
    knob's."""
    return [b for b in routing.factory_desk(profile) if b.layer == "preset"]


def file_desk(profile: str = "apc40") -> list[Binding]:
    """The desk the generator writes into the factory files: the fresh desk
    plus the four render toggles in their old place on the scene-launch
    column (`routing.TOGGLE_DESK_ROWS`). Plan 24 C1 made those controls
    invariant, but no file under hyperspace/library/ is rewritten in this
    run (decision 23), so the files keep the rows and the generator still
    writes them byte for byte; a load drops them quietly
    (`routing.RETIRED_DESK_ROWS`) and the session's rows do the same job.
    The creative pass that next regenerates the files can switch the
    generator to `fresh_desk` and the rows leave the files. Like the fresh
    desk it binds no track fader (plan 24 C2); a factory preset given
    faders gets them through `knob_desk(…, faders=…)`."""
    keep = routing.TOGGLE_DESK_ROWS
    return [b if b.layer == "preset" else replace(b, layer="preset")
            for b in routing.factory_desk(profile)
            if b.layer == "preset" or (b.source, b.target, b.op, float(b.value)) in keep]


# ---- the render graph (plan 26 A4) ----

GRAPH_KEY = "graph"
FX_GROUP = "fx"          # the effects' module group (`library/fx/*.json`): plan 33 R12


class GraphSection:
    """The loaded preset's ``graph`` section, landed (plan 26 A4).

    A preset may carry the render graph it wants as plain JSON
    (`graph.GraphSpec`: node instances and their wiring — never a param).
    Plan 36 T3 (W3): the section is all there is. A `/7` with none (or an
    empty one) is the empty frame — black, said (`NO_GRAPH_SAID`); a
    refused wire is dropped, said, never replaced by a default; a section
    this build cannot read at all (an unknown node kind, a bad value) is a
    note and black, never a crash — and that section is kept as the file
    had it, so a save does not throw away what a newer build wrote. (An
    old file reaches here only through the one-way migration,
    `graphmigrate.seven`.)

    Landing a graph (`land`) is a scene-setter over three objects:

    - **the registry**: an extra effect instance's params, `fx.acid.2.*`
      (`FxState.set_instances` + `fx.declare`: its own on, mix, order,
      clock — performance params, so the preset's `values` carry them),
      and an extra hands node's, `ghost.2.*` (`ghost.register`: the
      session's, like `ghost.*`, on a `GhostState` of its own that is
      kept while the app runs, so a preset that drops the node and one
      that brings it back find its settings as they were); and (plan 33
      S) each switch's `switch[.n].select` (`params.declare_switches`: a
      performance param, its pick in the preset's `values`); and (plan
      34 Z) each resize's `resize[.n].*` (`params.declare_resizes`, by its
      entry, reached or not);
    - **the renderer** (when attached, `attach`): `Renderer.wiring` (what
      the frame is built from: `graph.EMPTY` with nothing landed) and
      `Renderer.ghost_states` (the extra hands nodes' states, each drawn
      by its own `Ghost`);
    - (plan 36 T3) **the effects**: exactly the instances the section
      names exist (`FxState.hold`) — instance 1 of a file too.

    Owned by `Presets` (`Presets.graph`); the app and the tools attach the
    renderer."""

    def __init__(self, reg, fx=None, renderer=None, lib=None):
        self.reg = reg
        self.lib = lib                          # the open show's session seeds a new hands node
        self.fx = fx if fx is not None else getattr(reg, "fx_state", None)
        self.renderer = None
        self.spec: GraphSpec | None = None      # None: nothing landed (black)
        self.doc: dict | None = None            # the section a save writes (None: none)
        # plan 33 M: the section as the load wired it, when it is not `doc`
        # — a load's: `doc` is then the file's own section, as read, and
        # this the wired frame the load made of it, which a save writes
        # (row 394: always the newest, `/7`). None: `doc` is the section (a GRAPH edit's)
        self.free: dict | None = None
        self.states: dict[str, GhostState] = {}  # extra hands nodes' states, by node name
        self.declared: set[str] = set()         # the extra hands nodes whose params exist
        if renderer is not None:
            self.attach(renderer)

    def attach(self, renderer) -> None:
        """Hand the renderer the wiring and the hands states landed."""
        self.renderer = renderer
        self._push()

    @property
    def wiring(self) -> Wiring:
        return self.spec.wiring() if self.spec is not None else EMPTY

    def read(self, section) -> tuple[GraphSpec | None, dict | None, list[str]]:
        """(spec, the section to keep, notes) for a `/7` file's ``graph``
        value (None: the file has none). Reads, lands nothing.

        Plan 36 T3 (W3): nothing is filled in. No section, or an empty
        one, is the empty frame, said (`NO_GRAPH_SAID`); a wire or an entry
        this build refuses is dropped, said, and the section kept is the
        one that landed (`to_json`: a save writes what runs); a section it
        cannot read at all is black — (None, the file's section kept as it
        was, so a newer build's words survive a save, the note)."""
        if section is None or section == {} or section == {FRAME_KEY: WIRED_FRAME}:
            spec = read_graph({FRAME_KEY: WIRED_FRAME})
            return spec, spec.to_json(), [NO_GRAPH_SAID]
        files = self.files()
        try:
            spec = read_graph(section, effects=files)
        except GraphError as e:
            return None, copy.deepcopy(section), [f"graph: {e}; not read — black"]
        if not spec.wired:
            # (an old file's words: only the migration reads them)
            return None, copy.deepcopy(section), [UNWIRED_SAID]
        return spec, spec.to_json(), [f"graph: {n}; dropped" for n in spec.notes]

    def specs(self) -> dict[str, tuple[int, float]]:
        """Each effect file's and held instance's defaults, `(@order,
        @mix)` — what the migration to the free graph reads an absent value
        as (plan 33 M, `graphmigrate.Specs`); none with no FxState to ask.
        Plan 36 T3: every file on disk, held by the last graph or not."""
        return graphmigrate.specs_of(getattr(self, "fx", None))

    def files(self) -> set[str] | None:
        """The effect files on disk (None: no FxState to ask) — what a
        wire may name (plan 28 N4); plan 36 T3: held or not."""
        fx = getattr(self, "fx", None)
        if getattr(fx, "files", None):
            return set(fx.files)
        return ({fx.file_of(n) for n in fx.specs}       # (a stand-in FxState: its specs)
                if fx is not None and getattr(fx, "specs", None) else None)

    def land(self, spec: GraphSpec | None, doc: dict | None = None,
             free: dict | None = None) -> None:
        """Make `spec` the graph (None: the default): declare and drop the
        instances' params, and hand the renderer its wiring. `doc` is the
        section a save writes back; `free` (plan 33 M) the same graph in the
        free graph's words when `doc` is the file's from before them (a
        load: `free_doc`). With no `free` (an edit on the GRAPH page) `doc`
        is both. Plan 35 T3: every load's and every GRAPH edit's graph is a
        wired frame, and that is what a save writes (row 394: `/7`, plan 36 T3).

        An extra hands node declared for the first time this run starts
        from what the open show holds for it (`ghost.2.*` in its session —
        the show restored before the startup preset brought the node), so
        its settings survive a reopen and the show stays clean; after
        that its kept state is the live one."""
        wiring = spec.wiring() if spec is not None else EMPTY
        reg = self.reg
        want = {ghost_prefix(h.n): h.n for h in wiring.extra}
        for name in sorted(self.declared - set(want)):
            reg.remove_prefix(name + ".")
        for name, n in want.items():
            was = name in self.declared
            declare_ghost(reg, self.states.setdefault(name, GhostState()), n)
            if not was:
                self._seed(name)
        self.declared = set(want)
        if self.fx is not None:
            # plan 36 T3 (W3): the effects the section names, and no others
            changed = self.fx.hold(spec.effect_names() if spec is not None else frozenset())
            if changed:
                declare_fx(reg, self.fx, changed)
        # plan 33 S: each switch's `select`, as the effect instances' params
        declare_switches(reg, [sw.name for sw in spec.switches] if spec is not None else [])
        # plan 34 Z: each resize's values, by its entry — reached or not, so
        # an unwired resize keeps its knobs as an unwired switch its pick
        declare_resizes(reg, [z.name for z in spec.resizes] if spec is not None else [])
        # plan 36 T4: each extra look-back's own ring and trail, by its entry
        declare_lookbacks(reg, [lb.name for lb in spec.lookbacks] if spec is not None else [])
        self.spec, self.doc = spec, copy.deepcopy(doc)
        self.free = copy.deepcopy(free)
        self._push()

    def free_doc(self) -> dict | None:
        """The section in the free graph's words (plan 33 M; plan 35 T3: the
        wired frame every load lands): what a save writes (row 394: always
        `/7`) — `free` when the load kept the file's section beside it,
        else `doc`."""
        free = getattr(self, "free", None)      # (a section from before a hot reload)
        return free if free is not None else self.doc

    def _seed(self, name: str) -> None:
        """A newly declared hands node's params from the open show's
        session, where it holds them (`library.Project.session`) — once
        per show opened (`Project.opened`): after that the node's kept
        state is the live one, so a setting changed in this show is not
        put back when a later preset brings the node again."""
        project = getattr(getattr(self, "lib", None), "project", None)
        seeded = self.__dict__.setdefault("_seeded", {})
        show = getattr(project, "opened", None)
        if name in seeded and seeded[name] == show:
            return
        seeded[name] = show
        session = getattr(project, "session", None) or {}
        held = {pid: v for pid, v in session.items()
                if pid.startswith(name + ".") and pid in self.reg}
        if held:
            self.reg.restore(held)
        if project is not None and isinstance(getattr(project, "session", None), dict):
            # an id the show lacks takes the state this landing left, as a
            # show's `_apply` does for a param added since: the show stays clean
            for pid, v in self.reg.snapshot(part="session").items():
                if pid.startswith(name + "."):
                    project.session.setdefault(pid, v)

    def mark(self) -> tuple:
        """What is landed, for an undo of a load (`library.Marks`) — and
        (plan 36 T3) which effect instances exist (`FxState.held`)."""
        return (self.spec, copy.deepcopy(self.doc), copy.deepcopy(getattr(self, "free", None)),
                getattr(self.fx, "held", None))

    def put(self, mark: tuple) -> None:
        """Land what `mark` held again (an undo of a load), first. (A mark
        from before plan 33 holds no free section; one from before row 394
        held the retired values and the `/5` section a save below `/6`
        wrote, ignored now.)"""
        spec, doc, free = (*mark, None)[:3]
        if (spec, doc, free) != (self.spec, self.doc, getattr(self, "free", None)):
            self.land(spec, doc, free)
        # plan 36 T3: the instances that existed (every file, before a graph
        # had landed), as they were
        fx = self.fx
        if len(mark) > 3 and fx is not None and getattr(fx, "held", None) != mark[3]:
            changed = fx.hold(mark[3])
            if changed:
                declare_fx(self.reg, fx, changed)

    def _push(self) -> None:
        r = self.renderer
        if r is None:
            return
        r.wiring = self.wiring
        r.ghost_states = {name: self.states[name] for name in sorted(self.declared)}


# ---- desk templates (plan 24 C3) ----
#
# A preset's desk may start from a named template — a file in the library's
# `desk` group (`Library.desk_template`, ``hyperspace.desk/1``) — and add
# its own overrides:
#
#   {"schema": "hyperspace.preset/2", …,
#    "desk_template": "shape",                       the template's name
#    "desk": [row, …,                                 the overrides: each row
#             {"source": "cc:*:21", "dark": true}],    replaces every template
#                                                     row on its control; a
#                                                     dark row leaves that
#                                                     control unmapped
#
# A load expands it (`expand_desk`): the template's rows, less every one an
# override's control covers, then the override rows. A save writes the
# name and the overrides again, not the expanded rows (`compact_desk`), so
# a fix to the template lands in every preset that names it. A preset with
# no ``desk_template`` key is exactly as before: its ``desk`` is the whole
# preset layer. A template the library lacks is a note, and the overrides
# alone are the desk.
TEMPLATE_KEY = "desk_template"
DARK = "dark"
# plan 28 N1: the preset's modifier nodes (`modifiers.Modifier`), a list of
# entries after `routes` — ``{"id": "mod.1", "kind": "smooth", "in":
# ["hand:right.energy"], "attack": 0.05, "release": 0.6}``. No schema bump:
# an older build ignores the key (and a route on a ``mod:`` lane is a
# dormant row there). A desk template may carry the list too: a preset
# naming the template gets its modifiers, its own overriding by id
MODIFIERS_KEY = "modifiers"
# plan 28 N2: where the GRAPH page's nodes the look holds sit (the
# modifiers, the macros, the render nodes and their params) —
# ``{"<node id>": [x, y]}``, written after everything else, one node a
# line; the rig's nodes are the show's (library.LAYOUT). No key: laid out
# automatically, no note and no dirt. An older build ignores the key
LAYOUT_KEY = "layout"
# the performance groups with no module presets: a macro's meaning is its
# subscribers and a modifier's params are its entry, both the preset's
# (plan 33 S: a switch's pick means nothing without the preset's graph;
# plan 34 Z: nor a resize's values)
NO_MODULE = ("macro", modifiers.GROUP, SWITCH_GROUP, RESIZE_GROUP)


def _bank_prefix(pid: str) -> str:
    """A bank voice's param prefix, ``lfo.7.depth`` → ``lfo.7.``; "" for
    an id that names no voice (plan 31 B)."""
    head, _, rest = pid.partition(".")
    n, dot, _ = rest.partition(".")
    return f"{head}.{n}." if dot and n.isdigit() else ""


def merge_modifiers(template, own) -> tuple[list[dict], list[str]]:
    """The modifier entries a preset lands: the template's (in its order)
    with each one the preset's own list names by id replaced, then the
    preset's others. Either may be None. An entry that is not an object
    with an id is dropped with a note."""
    notes: list[str] = []

    def entries(lst, where):
        out = []
        for d in lst or ():
            if isinstance(d, dict) and isinstance(d.get("id"), str):
                out.append(d)
            else:
                notes.append(f"dropped a modifier entry in {where}: not an object with an id")
        return out
    mine = {d["id"]: d for d in entries(own, "the preset")}
    merged = [mine.pop(d["id"], d) for d in entries(template, "the desk template")]
    return merged + list(mine.values()), notes


def is_dark_row(row) -> bool:
    """An override row that leaves its control unmapped: ``{"source", "dark": true}``."""
    return isinstance(row, dict) and row.get(DARK) is True and isinstance(row.get("source"), str)


def template_doc(name: str, rows, note: str = "") -> dict:
    """A desk template's file: its name, an optional note, and the rows (a
    preset's ``desk`` form, `desk_json`). Written with `dumps`, a row a line."""
    doc: dict[str, Any] = {"schema": DESK_SCHEMA, "name": name}
    if note:
        doc["note"] = note
    doc["desk"] = desk_json(rows)
    return doc


def expand_desk(template: list[dict], overrides: list[dict]) -> list[Binding]:
    """The preset layer a template and a preset's overrides make: every
    template row whose control no override names (an override row, or a
    dark row, on an overlapping control — `Binding.overlaps`), in the
    template's order, then the override rows in theirs."""
    rows = [r for r in overrides if not is_dark_row(r)]
    own = [Binding.from_json(r) for r in rows]
    cover = own + [Binding(str(r["source"]), "") for r in overrides if is_dark_row(r)]
    kept = [t for t in (Binding.from_json(r) for r in template)
            if not any(c.overlaps(t) for c in cover)]
    return kept + own


def compact_desk(template: list[dict], live, keeps=None) -> list[dict]:
    """The overrides a save writes for a preset that names a template: the
    live preset layer's rows on every control where they differ from the
    template's (in the live order), then a dark row for each template
    control the live desk leaves unmapped (in the template's order).
    `keeps(row)` says whether a load keeps a template row (not on an
    invariant control, say): one it would drop is no difference.
    `expand_desk(template, compact_desk(template, live))` is `live` again,
    row for row, up to order — except a hand-edited desk holding two rows
    on one knob by two spellings (the template's ``cc:*:16`` and a
    ``cc:0:16``): the any-channel one is covered on the way back and lost."""
    tmpl = [b for b in (Binding.from_json(r) for r in template)
            if keeps is None or keeps(b)]
    by_t: dict[str, list[dict]] = {}
    for b, d in zip(tmpl, desk_json(tmpl)):
        by_t.setdefault(b.source, []).append(d)
    live = list(live)
    by_live: dict[str, list[dict]] = {}
    for d in desk_json(live):
        by_live.setdefault(d["source"], []).append(d)
    out = [d for src, ds in by_live.items() if by_t.get(src) != ds for d in ds]
    dark: list[str] = []
    for b in tmpl:
        if b.source in by_live or b.source in dark or any(x.overlaps(b) for x in live):
            continue
        dark.append(b.source)
    return out + [{"source": s, DARK: True} for s in dark]


def dumps(doc: dict) -> str:
    """A preset as file text: one route or desk row per line, so a diff
    reads as a binding; the values one per line."""
    parts = []
    for key, v in doc.items():
        if (key == GRAPH_KEY and isinstance(v, dict) and set(v) == {"nodes"}
                and isinstance(v["nodes"], list)):
            # the graph (plan 26 A4): one node per line, like a row
            rows = ",\n".join("  " + json.dumps(n) for n in v["nodes"])
            text = '{"nodes": [\n' + rows + '\n ]}' if v["nodes"] else '{"nodes": []}'
        elif (key == GRAPH_KEY and isinstance(v, dict) and set(v) == {"nodes", "wires"}
                and isinstance(v["nodes"], list) and isinstance(v["wires"], list)):
            # plan 28 N4: the nodes, then the wires, one a line
            halves = []
            for part in ("nodes", "wires"):
                rows = ",\n".join("  " + json.dumps(n) for n in v[part])
                halves.append(f'"{part}": [\n{rows}\n ]' if v[part] else f'"{part}": []')
            text = "{" + ",\n ".join(halves) + "}"
        elif (key == GRAPH_KEY and isinstance(v, dict) and v.get(FRAME_KEY) == WIRED_FRAME
                and set(v) <= {FRAME_KEY, "nodes", "wires"}
                and all(isinstance(v.get(k, []), list) for k in ("nodes", "wires"))):
            # row 394: the wired frame every save writes — the marker, then
            # the nodes and the wires, one a line
            halves = [f'"{FRAME_KEY}": {json.dumps(v[FRAME_KEY])}']
            for part in ("nodes", "wires"):
                if part not in v:
                    continue
                rows = ",\n".join("  " + json.dumps(n) for n in v[part])
                halves.append(f'"{part}": [\n{rows}\n ]' if v[part] else f'"{part}": []')
            text = "{" + ",\n ".join(halves) + "}"
        elif key == LAYOUT_KEY and isinstance(v, dict) and v:
            # the GRAPH page's positions (plan 28 N2): one node a line
            rows = ",\n".join(f"  {json.dumps(k)}: {json.dumps(xy)}" for k, xy in v.items())
            text = "{\n" + rows + "\n }"
        elif (key == MEDIA_KEY and isinstance(v, dict) and set(v) == {"channels"}
                and isinstance(v["channels"], dict) and v["channels"]):
            # plan 32: the bins, one channel a line
            rows = ",\n".join(f"  {json.dumps(c)}: {json.dumps(b)}"
                               for c, b in v["channels"].items())
            text = '{"channels": {\n' + rows + '\n }}'
        elif key in ("routes", MODIFIERS_KEY, "desk") and isinstance(v, list):
            if v:
                rows = ",\n".join("  " + json.dumps(r) for r in v)
                text = f"[\n{rows}\n ]"
            else:
                text = "[]"
        elif isinstance(v, dict) and v:
            text = json.dumps(v, indent=1).replace("\n", "\n ")
        else:
            text = json.dumps(v)
        parts.append(f" {json.dumps(key)}: {text}")
    return "{\n" + ",\n".join(parts) + "\n}\n"


def echo_seconds(doc: dict) -> tuple[dict, list[str]]:
    """A preset document with the look-back's per-frame ids read as 60 Hz
    frames and written in seconds (plan 14 WP6, `lookback.LEGACY`): its
    values, every route and desk row on one, a macro's base subscriber on
    one (its from / to converted too) and a depth subscriber naming such a
    route. Returns (a copy, a note per change); the document itself when
    it names none."""
    text = json.dumps(doc)
    if not any(k in text for k in LEGACY):
        return doc, []
    out = copy.deepcopy(doc)
    values, notes = migrate_values(dict(out.get("values") or {}))
    if "values" in out:
        out["values"] = values
    for key in ("routes", "desk"):
        rows = []
        for row in out.get(key) or []:
            new, note = migrate_row(row, doc.get("values") or {}) \
                if isinstance(row, dict) else (row, None)
            if note:
                notes.append(f"{key}: {note}")
            rows.append(new)
        if key in out:
            out[key] = rows
    for mid, m in (out.get("macros") or {}).items():
        for s in (m.get("subs") or []) if isinstance(m, dict) else []:
            if not isinstance(s, dict):
                continue
            # a subscriber's from / to default to 0 and 1 (routing.Sub):
            # written out, so the converted ends are the file's own
            base = s.get("base")
            if base in LEGACY:
                new, conv = LEGACY[base]
                s["base"] = new
                for end, default in (("from", 0.0), ("to", 1.0)):
                    try:
                        s[end] = conv(s.get(end, default))
                    except (TypeError, ValueError):
                        notes.append(f"{mid}: base {base} {end} {s.get(end)!r} not a number")
                notes.append(f"{mid}: base {base} → {new}")
            dep = s.get("depth")
            if isinstance(dep, dict) and dep.get("target") in LEGACY:
                old = dep["target"]
                dep["target"] = LEGACY[old][0]
                notes.append(f"{mid}: depth on {old} → {dep['target']}")
                # the subscriber sets the route's depth: its ends move to
                # fade's units the way the route's own depth did
                if old == "dream.decay":
                    for end, default in (("from", 0.0), ("to", 1.0)):
                        d = fade_depth(s.get(end, default), dep.get("source"),
                                       doc.get("values") or {})
                        if d is None:
                            notes.append(f"{mid}: depth {end} {s.get(end)!r} not a number")
                        else:
                            s[end] = d
    return out, notes


class Presets:
    """The loaded preset over one library, registry and router.

    Built as ``Presets(lib, reg, router)`` once the router exists (app.main);
    it registers the ``presets`` document kind and makes itself
    ``lib.presets``, which the project's bank (F-keys, the preset row)
    loads and saves through. The kind's hooks look this object's methods
    up at call time, so a hot reload that re-classes it reaches them."""

    def __init__(self, lib, reg, router):
        self.lib, self.reg, self.router = lib, reg, router
        self.note = ""
        self.notes: list[str] = []       # step 1's notes from the last load
        self.migrated = ""               # plan 36 T3: "/N migrated to /7" when that load was old
        self.desk_notes: list[str] = []  # the desk rows the last load dropped (set_desk)
        # plan 28 N2: the GRAPH page's positions of the look's nodes
        self.layout: dict[str, list[float]] = {}
        # R17 (final review): the live preset came from `new` and has never
        # been saved — save names it (whatever a file of its name holds);
        # a load or a save clears it (`_landed`)
        self.unsaved = False
        # plan 26 A4: the loaded preset's graph section (its instances'
        # params, the renderer's wiring once one is attached)
        self.graph = GraphSection(reg, lib=lib)
        lib.kind(GROUP, SCHEMA.rpartition("/")[0],
                 load=lambda doc, path: self.load_doc(doc, path),
                 document=lambda name: self.document(name),
                 signature=lambda: self.signature(),
                 versions=VERSIONS,
                 text=lambda doc: dumps(doc))
        lib.on_load(GROUP, lambda name: self._landed(name))
        # plan 33 R12: an fx module loaded replaces the graph's runs
        self._watch_fx_modules()
        lib.presets = self
        self.listeners: list = []        # called with the name after every load (app.py)

    # ---- the API ----

    @property
    def media(self):
        """The eight media channels the registry's ``media.*`` params write
        (`build_registry`'s `media`, plan 32): their bins are this preset's
        ``media`` section. None on a registry from before plan 32."""
        return getattr(self.reg, "media", None)

    @property
    def current(self) -> str | None:
        return self.lib.current(GROUP)

    def load(self, name: str) -> list[str]:
        """Load a preset by name through the library (which records it as
        the strip's current and its clean reference); returns the ids the
        file names that nothing has."""
        missing = self.lib.load(GROUP, name)
        self._warn(name)
        return missing

    def save_as(self, name: str) -> Path:
        """The live state as a user preset (a factory one of that name is
        shadowed, never overwritten)."""
        return self.lib.save_as(GROUP, name)

    def new(self, at: tuple[float, float] = (0.0, 0.0)) -> list[str]:
        """A new preset (plan 35 T7, row 387): the library's fresh values
        for every performance group (the reset `Project.new` uses, so
        nothing of the preset loaded before survives), no routes, the desk
        written out as the factory preset layer (a file with no `desk` key
        gets that layer and `"desk": []` an empty one — the blank preset
        says which), and (plan 36 T5, W5) a section of the scene chain
        alone — `shape → scene → output.all.image`, plain faces
        (`graphview.SCENE_CHAIN`) — so, with the rig's bus cables, a shape
        on every window. Its three nodes are laid left to right in the
        preset's layout map from `at` (layout units: the GRAPH page's
        `ui_graph.in_view`), not left to the automatic layout. The
        session's params stay. One undo step, named `untitled`, dirty and
        `unsaved` (R17) until it is saved."""
        lib, reg = self.lib, self.reg
        undo.push("new preset", load=True)    # the load below joins this step
        values = {k: v for k, v in lib._fresh_all().items()
                  if k in reg and reg[k].group in PERFORMANCE_GROUPS
                  and reg[k].group != modifiers.GROUP and reg[k].persist
                  and not is_instance_id(k) and not is_switch_id(k)
                  and not is_resize_id(k) and not is_lookback_id(k)}
        doc = {"schema": WIRED_SCHEMA, "name": UNTITLED_PRESET, "values": values,
               "routes": [], "macros": {}, "modules": {},
               "desk": desk_json(fresh_desk(self.router.table.profile)),
               GRAPH_KEY: read_graph({FRAME_KEY: WIRED_FRAME, "wires": [
                   {"from": a, "to": b} for a, b in graphview.SCENE_CHAIN]}).to_json(),
               LAYOUT_KEY: graphview.chain_layout(graphview.NEW_CHAIN, at)}
        lib.land_unsaved(GROUP, UNTITLED_PRESET, doc)
        self.unsaved = True               # (after the load hook cleared it)
        lib.say(NEW_SAID)
        return [NEW_SAID]

    def load_doc(self, doc: dict, path: Path | None = None) -> list[str]:
        """Apply a preset document — the kind's loader (plan 13 §5).
        Returns the unknown ids; the notes land in `notes`."""
        lib, reg, table = self.lib, self.reg, self.router.table
        notes: list[str] = []
        # plan 33 R12: (again on every load — a Presets from before a hot
        # reload brought this method never ran the __init__ that registers it)
        self._watch_fx_modules()
        # 0. the look-back's per-frame ids, read as 60 Hz frames (plan 14
        #    WP6) — a file the launch's migration has not rewritten
        doc, converted = echo_seconds(doc)
        if converted:
            notes.append(f"look-back read in seconds ({converted[0]}"
                         + (f", +{len(converted) - 1}" if len(converted) > 1 else "")
                         + "); save to keep it")
        # 0. and its camera.pan in world units (plan 26 A2): a file from
        #    before stored px. Silent — the shape lands where it was, and a
        #    factory file is read this way on every load
        doc, _ = pan_world(doc)
        # 0. and its palette as a slice of the HSV cylinder (plan 30 N8): a
        #    file from before stored the fold's centre/width and sat/val
        #    lo/hi. Silent, as the pan is, but for a fold wider than the
        #    slice reproduces
        doc, palette_notes = palette_slice(doc)
        notes += palette_notes
        # 0. and its render graph (plan 26 A4): read, not yet landed. Plan
        #    36 T3 (W3): a `/7` is read as it is — no section is the empty
        #    frame, black, said; nothing is filled in. An older file is
        #    first rewritten as its `/7` by the one-way migration
        #    (`graphmigrate.seven`, said): the free graph (plan 33 M), the
        #    wired frame in the new ids (plan 35), every hidden edge and D1
        #    placement as its wire, the values of an effect the section does
        #    not name dropped — a desk template's rows counted as the desk
        #    they expand to — and a save writes that `/7` (row 394)
        gs = self._graph_section()
        template_rows = self._template_rows(doc)
        migrate_notes: list[str] = []
        migrated = ""
        version = graphmigrate.schema_version(doc)
        if version is None or version < graphmigrate.SEVEN:
            old = str(doc.get("schema"))
            doc, migrate_notes = graphmigrate.seven(doc, gs.specs(), desk=template_rows)
            # (said on the strip — `_warn` — but no problem with the file:
            # not one of `notes`, which say what did not land)
            migrated = graphmigrate.MIGRATED_NOTE.format(old=old, new=WIRED_SCHEMA)
        spec, section, graph_notes = gs.read(doc.get(GRAPH_KEY))
        notes += graph_notes
        # 1. what the file names that a preset may not carry — all parsed
        #    before anything lands, so a bad row leaves the state alone. An
        #    id of a node instance (`fx.acid.2.mix`, `ghost.2.on`) is looked
        #    at once this file's graph has landed — against the params that
        #    graph holds, never the ones the last preset's graph left
        values: dict[str, Any] = {}
        unknown: list[str] = []
        later: dict[str, Any] = {}
        # plan 31 B: each bank's membership (``"lfos": [1, 3, 7]``; none in
        # the file, the default four), declared before the values land — so
        # a knob of a voice this registry lacks yet waits in `later`
        members: dict[str, list[int]] = {}
        for scheme, bank in self._banks().items():
            members[scheme], bank_notes = bank.parse(doc.get(bank.KEY))
            notes += bank_notes
        bank_ids = {f"{s}.{n}." for s, ids in members.items() for n in ids}
        bmp_alpha: dict[str, Any] = {}    # an old view.bmp_alpha, by the id it stands for
        for pid, v in dict(doc.get("values") or {}).items():
            p = reg.get(pid)
            if p is None and _bank_prefix(pid) in bank_ids:
                later[pid] = v
            elif pid.startswith(BMP_PREFIX):
                # plan 32 (row 331): the one bitmap file is gone; the faces
                # read a media channel (view.media). Its values are dropped
                # and the file it named is said — but for the alpha, whose
                # alias (params.BMP_ALPHA) lands it on view.media_alpha
                if p is not None and p.alias:
                    bmp_alpha[reg.real(p).id] = v
                elif pid == "view.bmp_file" and v:
                    notes.append(f"bitmap file {v} is no longer read: put it on a media channel")
            elif pid.startswith(modifiers.PREFIX):
                # a modifier's param is set by its entry (`modifiers`), never here
                notes.append(f"{pid} is a modifier's: set in its entry, ignored")
            elif (is_instance_id(pid) or is_switch_id(pid) or is_resize_id(pid)
                  or is_lookback_id(pid)
                  or graphmigrate.effect_of(pid) is not None):
                # (plan 33 S: a switch's `select` too — its graph declares it;
                # plan 34 Z: and a resize's values; plan 36 T3: and every
                # effect's — instance 1 exists only where its graph names it)
                later[pid] = v
            elif p is None:
                unknown.append(pid)
            elif part_of(p) == "session":
                notes.append(f"{pid} is the session's, ignored")
            elif part_of(p) is None or not p.persist:
                notes.append(f"{pid} is not part of a preset, ignored")
            else:
                values[pid] = v
        for pid, v in bmp_alpha.items():      # the file's own new id wins
            values.setdefault(pid, v)
        if unknown:
            shown = ", ".join(unknown[:4]) + ("…" if len(unknown) > 4 else "")
            notes.append(f"{len(unknown)} unknown id(s): {shown}")
        # plan 32 S: the media section's bins, read now, landed with the
        # values; no section is every bin empty
        bins, media_notes = media_channels.read_bins(doc.get(MEDIA_KEY))
        notes += media_notes
        routes: list[Binding] = []
        for row in doc.get("routes") or []:
            b = Binding.from_json(row)
            if not is_continuous(b.scheme) or b.op not in MOD_OPS:
                notes.append(f"dropped {b.source} → {b.target} ({b.op}): not a performer row")
                continue
            # a route on a param no performer may drive — one saved before
            # it stopped being modulatable (ghost.mirror / .guide /
            # .tethers, plan 21 R12) — is dropped with a note; the file is
            # not rewritten. An id this build lacks is kept (dormant)
            tp = reg.get(b.target)
            if tp is not None and not tp.modulatable:
                notes.append(f"dropped {b.source} → {b.target}: not modulatable")
                continue
            routes.append(b)
        # no `desk` key: a fresh preset's, the factory preset layer; an
        # explicit [] is an empty one (every preset control dark, D8). A
        # `desk_template` (plan 24 C3): the template's rows with `desk` as
        # its overrides; a template the library lacks is a note, and the
        # overrides alone are the desk
        tmods = None                      # the template's modifiers (plan 28 N1)
        if doc.get(TEMPLATE_KEY):
            name = str(doc[TEMPLATE_KEY])
            try:
                tdoc = lib.desk_template(name)
                # (plan 33 M: as the migration read it, a row on a channel
                # choice on its switch)
                template = template_rows if template_rows is not None else tdoc["desk"]
            except LibraryError as e:
                notes.append(f"desk template {name!r} not loaded ({e}): this preset's own "
                             "desk rows only")
                tdoc, template = {}, []
            tmods = tdoc.get(MODIFIERS_KEY)
            desk = expand_desk(template, list(doc.get("desk") or []))
            # the template's rows as this load expanded them: a save
            # compacts against these, so a template fixed on disk after the
            # load (the live desk is not re-expanded) cannot turn its fix
            # into overrides that undo it (`_desk_part`)
            key = str(doc.get("name") or (path.stem if path else ""))
            self._at_load()[key] = (name, copy.deepcopy(template))
            self._mods_at_load()[key] = (name, copy.deepcopy(list(tmods or [])))
        elif "desk" in doc:
            desk = [Binding.from_json(row) for row in doc.get("desk") or []]
        else:
            desk = fresh_desk(table.profile)
        # plan 28 N1: the modifiers, read before the routes land — the
        # template's, the preset's own over them by id; each parsed now, so
        # a route onto a ``mod:<n>`` lane no modifier publishes is dropped
        # with a note, like a route onto a param no performer may drive
        mod_docs, mod_notes = merge_modifiers(tmods, doc.get(MODIFIERS_KEY))
        notes += mod_notes
        mods: list[Modifier] = []
        for d in mod_docs:
            try:
                m = Modifier.from_json(d)
            except (ValueError, TypeError) as e:
                notes.append(f"dropped modifier {d.get('id')}: {e}")
                continue
            if any(x.id == m.id for x in mods):
                notes.append(f"dropped a second {m.id}")
                continue
            mods.append(m)
        have = {m.id for m in mods}
        kept_routes = []
        for b in routes:
            mid = modifiers.id_of(b.source)
            if b.head == modifiers.SCHEME and mid not in have:
                notes.append(f"dropped {b.source} → {b.target}: no modifier "
                             f"{mid or b.source}")
                continue
            kept_routes.append(b)
        routes = kept_routes
        # a bad subscriber raises before anything lands; a route's scale is
        # settled as the table's are (decision register row 18 (a)): on a
        # macro a depth subscriber, on a performance param dropped, noted
        held = routing.macros_of(doc.get("macros"))
        notes += routing.migrate_scales(routes, held)
        macros = {mid: m.to_json() for mid, m in held.items()}
        modules = dict(doc.get("modules") or {})
        for group in list(modules):
            if group not in PERFORMANCE_GROUPS or group in NO_MODULE:
                notes.append(f"module {group}: not a performance group, ignored")
                modules.pop(group)
        # the file parsed, nothing landed yet: one undo step for the whole
        # load, by whichever road it came (undo.py, plan 15 WP1) — with
        # what is loaded now, so undoing it puts the earlier name back too
        undo.push(f"load {doc.get('name') or (path.stem if path else 'preset')}", load=True)
        # 1½. the graph lands first (plan 26 A4): its instances' params
        #     exist before their values do; the ids read for it are sorted now
        held_graph, held_values = gs.mark(), reg.snapshot(part="performance")
        # (membership and every bank voice's values, before anything moves)
        held_mods = table.modifiers_doc(reg)
        held_banks = {s: b.doc() for s, b in self._banks().items()}
        # from here to the values landing, anything that raises puts the
        # graph that was there back, with its instances' values: a load is
        # refused whole, never half a graph
        try:
            gs.land(spec, section)
            # R19 (row 354: "rebuilds, not loads"): a load's delays start
            # empty — no trail of the preset before in this one
            reset = getattr(gs.renderer, "reset_delays", None)
            if callable(reset):
                reset()
            # the modifiers and their params (plan 28 N1), landed with the
            # values: their entries are their params' values
            notes += table.set_modifiers(mods, reg)
            values.update(reg.snapshot(group=modifiers.GROUP))
            for scheme, ids in members.items():          # plan 31 B: the banks
                self._banks()[scheme].set(ids)
            late: list[str] = []
            for pid, v in later.items():
                p = reg.get(pid)
                if p is None:
                    late.append(pid)
                elif part_of(p) == "session":
                    notes.append(f"{pid} is the session's, ignored")
                elif part_of(p) is None or not p.persist:
                    notes.append(f"{pid} is not part of a preset, ignored")
                else:
                    values[pid] = v
            if late:
                unknown += late
                notes.append(f"{len(late)} unknown id(s): " + ", ".join(late[:4])
                             + ("…" if len(late) > 4 else ""))
            # 2. every performance param: the file's value, else its group default
            by_group: dict[str, dict[str, Any]] = {g: {} for g in PERFORMANCE_GROUPS}
            for pid, v in values.items():
                by_group[reg[pid].group][pid] = v
            landed: dict[str, Any] = {}
            for group in PERFORMANCE_GROUPS:
                landed.update(lib.resolved(group, by_group[group]))
            # a value that will not take (a hand-edited "fast" on a number)
            # must not leave half the look on this preset and half on the
            # last: the state as it was goes back and the load is refused whole
            before = reg.snapshot(part="performance")
            try:
                lib.restore(landed)
            except (ValueError, TypeError) as e:
                lib.restore(before)
                raise ValueError(f"a value would not land ({e}); nothing loaded") from e
        except BaseException:
            if table.modifiers_doc(reg) != held_mods:     # the modifiers as they were
                table.set_modifiers(held_mods, reg)
            for scheme, ids in held_banks.items():        # the banks as they were
                bank = self._banks()[scheme]
                if bank.doc() != ids:
                    bank.set(ids)
            if gs.mark() != held_graph:          # the graph as it was
                gs.put(held_graph)
            # then every value as it was — the graph instances', and a bank
            # voice's that the load removed and the line above re-added
            # fresh (`held_values` was taken before `bank.set`): a refused
            # load leaves LFO 5's depth where it stood, not at its default
            lib.restore({k: v for k, v in held_values.items() if k in reg})
            raise
        # 2½. the bins (plan 32): each channel opens what its slot names at
        #     the next frame's poll
        media = self.media
        if media is not None:
            media.set_bins(bins)
        # 3. every performer row replaced; the referee keeps the first
        table.set_routes(routes)
        notes += [f"dropped {b.source} → {b.target}: {why}" for b, why in table.dropped]
        # 4. the desk's preset layer replaced; the layer drops to it (D4)
        #    and the MIDI adapter redraws, the faders' catch cleared
        self.desk_notes = table.set_desk(desk)
        notes += self.desk_notes
        # 5. the macros replaced, their base subscribers landed now from the
        #    macro bases step 2 put down — the macro is the scene-setter of
        #    record, so its subscriber's value stands over `values`; a base
        #    subscriber on a session param is dropped with a note (D9)
        notes += table.set_macros(macros, reg)
        self.router.follow_macros(force=True)
        # 5½. plan 33 M: an effect the migration left out of the run, said
        #     only while a row that landed drives it (a desk row on an
        #     invariant control, dropped above, drives nothing)
        driven = graphmigrate.targets({"routes": [b.to_json() for b in table.routes()],
                                       "desk": desk_json(table.desk()),
                                       "macros": table.macros_doc()})
        for note in migrate_notes:
            name = graphmigrate.left_out_of(note)
            if name is None or any(graphmigrate.effect_of(t) == name for t in driven):
                notes.append(note)
        self.note = str(doc.get("note") or "")
        # 6. the module labels: a label and a clean dot, never a load (D3)
        for group in PERFORMANCE_GROUPS:
            if group in NO_MODULE:
                continue
            label = modules.get(group)
            lib.label(group, str(label) if label else None)
        # 6½. where the GRAPH page's nodes sit (plan 28 N2): none is the
        #     automatic layout; an entry that is not a name and two numbers
        #     is dropped with a note; an old canvas id is read in today's
        #     (R14), and a save writes today's (row 394)
        positions, bad = read_positions(doc.get(LAYOUT_KEY))
        self.layout = graphmigrate.renamed_layout(positions)
        if bad:
            notes.append(f"layout: {bad} entr{'y' if bad == 1 else 'ies'} unreadable, ignored")
        # 7. the notes, for the panel
        self.notes = notes
        self.migrated = migrated            # plan 36 T3: the one-way migration's word
        self._warn(str(doc.get("name") or (path.stem if path else "preset")))
        return unknown

    def document(self, name: str) -> dict:
        """The live state as a preset document, named — what a save writes."""
        lib = self.lib
        modules = {g: lib.current(g) for g in PERFORMANCE_GROUPS
                   if g not in NO_MODULE and lib.current(g)}
        # row 394 (the owner, 2026-10-25): every save is the newest schema,
        # in today's words — both Macs run the same build, so nothing is
        # written down for an older one (D1's lowest-schema rule, R10 and
        # R15 are superseded)
        doc: dict[str, Any] = {"schema": WIRED_SCHEMA, "name": name}
        if self.note:
            doc["note"] = self.note
        table = self.router.table
        # plan 26 A4: the graph the loaded preset carried — plan 35 T3: the
        # wired frame the load or the GRAPH page landed; plan 36 T3: with
        # none landed (nothing loaded yet) the empty frame the renderer
        # draws for none (`graph.EMPTY`), black, so what a save writes is
        # what was drawn
        gs = self._graph_section()
        section = gs.free_doc()
        if section is None:
            section = read_graph({FRAME_KEY: WIRED_FRAME}).to_json()
        doc[GRAPH_KEY] = copy.deepcopy(section)
        # plan 31 B: a bank's membership, only where it is not the default —
        # a preset of four LFOs writes the file it always did
        for bank in self._banks().values():
            if bank.doc() != list(bank.DEFAULT):
                doc[bank.KEY] = bank.doc()
        values = self._values()
        # plan 36 T3 (W3): an effect exists only where the section names it
        # — the values of one it does not (a rig's, before any graph
        # landed) are not the preset's
        held = graphmigrate.section_effects(doc[GRAPH_KEY])
        values = {k: v for k, v in values.items()
                  if graphmigrate.effect_of(k) in (None, *held)}
        doc.update(values=values,
                   routes=[b.to_json() for b in table.routes()],
                   **self._modifiers_part(name),
                   **self._desk_part(name), macros=table.macros_doc(),
                   modules=modules, **{UNITS_KEY: dict(UNITS)})
        layout = getattr(self, "layout", None)
        if layout:                      # plan 28 N2: a preset with none writes none
            doc[LAYOUT_KEY] = {k: list(layout[k]) for k in sorted(layout)}
        # plan 32 S: the channels' bins
        media = self.media
        if media is not None:
            doc[MEDIA_KEY] = media.to_json()
        return doc

    def _banks(self) -> dict:
        """The router's modulator banks by scheme (plan 31 B); none on a
        router that steps none (the tests' bare ones)."""
        banks = getattr(self.router, "_banks", None)
        return banks() if callable(banks) else {}

    def _values(self) -> dict[str, Any]:
        """The preset's `values`: every performance base but the modifiers'
        params, which their entries hold (so a file saved here loads on an
        older build with no unknown id)."""
        return {k: v for k, v in self.reg.snapshot(part="performance").items()
                if not k.startswith(modifiers.PREFIX)}

    def _mods_at_load(self) -> dict[str, tuple[str, list[dict]]]:
        """preset name → (its template's name, the template's modifier
        entries as the load read them) — `_at_load`'s twin for the
        modifiers. On the instance, made on first use."""
        return self.__dict__.setdefault("_template_mods_at_load", {})

    def _modifiers_part(self, name: str | None = None) -> dict:
        """What a save writes for the modifiers: ``{"modifiers": entries}``
        after the routes, or nothing when there are none. A preset that
        names a desk template writes only the entries that differ from the
        template's (as the load read them), so a template's modifier fixed
        on disk reaches it at the next load. (A template's modifier the
        preset removed comes back at the next load: no entry says "none".)"""
        live = self.router.table.modifiers_doc(self.reg)
        ref = self.template_of_loaded()
        tmods: list[dict] = []
        if ref is not None:
            held = self._mods_at_load().get(self.lib.current(GROUP) or "")
            if held is not None and held[0] == ref:
                tmods = held[1]
            else:
                try:
                    tmods = list(self.lib.desk_template(ref).get(MODIFIERS_KEY) or [])
                except LibraryError:
                    tmods = []
            if name is not None:
                self._mods_at_load()[name] = (ref, copy.deepcopy(tmods))
        theirs: dict[str, dict] = {}
        for d in tmods:
            try:
                m = Modifier.from_json(d)
            except (ValueError, TypeError):
                continue
            theirs[m.id] = m.to_json()
        own = [d for d in live if not undo.alike(theirs.get(d["id"]), d)]
        return {MODIFIERS_KEY: own} if own else {}

    def _watch_fx_modules(self) -> None:
        """Hand the library's fx module loads to `_fx_module` (plan 33 R12,
        `Library.on_apply`): idempotent, so `load_doc` calls it as well as
        `__init__` and a hot reload that re-classes this object (never
        re-inits it) is registered at its next preset load. The hook looks
        the method up at call time, so a re-class reaches it."""
        on_apply = getattr(self.lib, "on_apply", None)
        if on_apply is not None:
            on_apply(FX_GROUP, lambda name, doc: self._fx_module(name, doc))

    def _fx_module(self, name: str, doc: dict) -> None:
        """An fx module just landed (plan 33 R12, `Library.on_apply`): its
        run replaces the loaded graph's main run, and its faces run the
        faces' when it has one (`graphmigrate.module_runs`); every branch,
        composite, switch and placement stays. Its values are the fx group
        as the module landed them. A wire the loaded graph had refused stays
        refused, as the load said, and the rest lands with the module's run
        (the load's own landing: the spec without it, the section with it).
        A graph this build cannot read at all is left as it is, said in a
        note; one that comes out the same is not landed again."""
        gs = self._graph_section()
        table = self.router.table
        rows = {"routes": [b.to_json() for b in table.routes()],
                "desk": desk_json(table.desk()), "macros": table.macros_doc()}
        before = gs.free_doc()
        if before is None:
            # (plan 36 T4, the T3 review's WYSIWYG leak: before any preset
            # has landed the frame is the empty wired one — the module's run
            # goes into it, and nothing of today's frame is filled in)
            before = read_graph({FRAME_KEY: WIRED_FRAME}).to_json()
        # (its order and target are no params since plan 33 T7: read from
        # the module's file over the group's defaults, as its values land)
        own = self._held_retired(_module_values(FX_GROUP, doc), (FX_GROUP,))
        # (plan 36 T3: an effect the graph does not name has no params yet —
        # the module's own values say whether it joins the run)
        landed = {**self.lib.defaults(FX_GROUP), **_module_values(FX_GROUP, doc),
                  **self.reg.snapshot(FX_GROUP)}
        new, notes = graphmigrate.module_runs(before, {**landed, **own}, gs.specs(), rows)
        spec, section, read_notes = gs.read(new)
        if spec is None:
            notes = [*notes, ("its run is not applied — the preset's graph is not one "
                              "this build reads")]
        else:
            notes = [*notes, *read_notes]
        # (final review, finding 1: every note the module's run makes is
        # said — a run refused here would otherwise vanish without a word;
        # one the preset's load already said is not said twice)
        said = list(getattr(self, "notes", []))
        for note in (f"fx module {name}: {n}" for n in notes):
            if note not in said and not any(n == note.partition(": ")[2] for n in said):
                said.append(note)
                self.lib.say(warning=note)
        self.notes = said
        if spec is None:
            return
        if section != before:
            gs.land(spec, section)

    def _held_retired(self, values: dict, groups=PERFORMANCE_GROUPS) -> dict[str, Any]:
        """The retired values (plan 33 T7) a load of `values` (a file's, or
        an fx module's) lands, as a build from before T7 landed them —
        `graphmigrate.landed_retired` over the groups' defaults
        (`Library.defaults`) and the effects this build holds: an fx
        module's run is read from its orders (`_fx_module`)."""
        defaults: dict[str, Any] = {}
        for g in groups:
            try:
                defaults.update(self.lib.defaults(g))
            except (LibraryError, AttributeError, KeyError):   # a stand-in library
                continue
        return graphmigrate.landed_retired(
            values, defaults, self._graph_section().specs(), effects=FX_GROUP in groups,
            channels=bool({"view", "backdrop"} & set(groups)))

    def _template_rows(self, doc: dict) -> list | None:
        """A copy of the rows of the desk template `doc` names (plan 24 C3),
        or None: none named, or one the library lacks (the load says so when
        it expands the desk)."""
        name = doc.get(TEMPLATE_KEY)
        if not name:
            return None
        try:
            return copy.deepcopy(list(self.lib.desk_template(str(name))["desk"]))
        except (LibraryError, KeyError, TypeError):
            return None

    def _graph_section(self) -> GraphSection:
        """The graph section's lander; made here for a `Presets` from
        before plan 26 A4 (a hot reload re-classes, never re-inits)."""
        gs = self.__dict__.get("graph")
        if gs is None:
            gs = self.graph = GraphSection(self.reg, lib=self.lib)
        return gs

    def template_of_loaded(self) -> str | None:
        """The desk template the loaded preset's file names (plan 24 C3),
        or None: read from the file, so an undo that puts an earlier preset
        back puts its template back too."""
        cur = self.lib.current(GROUP)
        if not cur:
            return None
        try:
            ref = self.lib.read(GROUP, cur).get(TEMPLATE_KEY)
        except LibraryError:
            return None
        return str(ref) if ref else None

    def _at_load(self) -> dict[str, tuple[str, list[dict]]]:
        """preset name → (its template's name, the template's rows as the
        load that expanded the live desk read them). On the instance, made
        on first use (a `Presets` from before a hot reload has none)."""
        return self.__dict__.setdefault("_templates_at_load", {})

    def template_at_load(self) -> tuple[str, list[dict]] | None:
        """The loaded preset's (template name, template rows as its load
        read them), or None — what a save compacts against (plan 28 N5:
        the GRAPH page's template node reads it)."""
        return self._at_load().get(self.lib.current(GROUP) or "")

    def _desk_part(self, name: str | None = None) -> dict:
        """What a save writes for the desk: ``{"desk": rows}``, the whole
        preset layer — or, when the loaded preset names a desk template,
        ``{"desk_template": name, "desk": overrides}`` (`compact_desk`),
        the reference and not the expanded rows. The overrides are taken
        against the template **as the load read it**, so a template file
        fixed since then changes no override (the fix lands at the next
        load). A template the library lacks counts as empty: every live
        row is an override. `name`: the preset this save writes, which
        then holds the same template rows."""
        table = self.router.table
        ref = self.template_of_loaded()
        if ref is None:
            return {"desk": desk_json(table.desk())}
        held = self._at_load().get(self.lib.current(GROUP) or "")
        if held is not None and held[0] == ref:
            template = held[1]                  # as the load expanded it
        else:
            try:
                template = self.lib.desk_template(ref)["desk"]
            except LibraryError:
                template = []
        if name is not None:                     # the file now written holds these too
            self._at_load()[name] = (ref, copy.deepcopy(template))
        inv = table.invariant_rows()

        def keeps(b: Binding) -> bool:          # what `set_desk` keeps of a template row
            return (b.is_midi and routing.save_refusal(b) is None
                    and not table.is_invariant(b, inv))
        return {TEMPLATE_KEY: ref, "desk": compact_desk(template, table.desk(), keeps)}

    def signature(self) -> tuple:
        """What the strip's dirty dot compares: the performance bases, the
        performer rows, the desk's preset layer and the macros, each as it
        would be written — and the graph section (plan 26 A4; None for a
        preset with none, so a file from before it is never dirty)."""
        table = self.router.table
        # (plan 33 M: in the free graph's words, so a change to the run alone
        # — which a pre-33 section says in values — dirties the preset too)
        section = self._graph_section().free_doc()
        return (self._values(),
                json.dumps([b.to_json() for b in table.routes()]),
                json.dumps(desk_json(table.desk()), sort_keys=True),
                json.dumps(table.macros_doc(), sort_keys=True),
                None if section is None else json.dumps(section, sort_keys=True),
                table.modifiers_doc(self.reg),
                # plan 31 B: an LFO added or removed
                {s: b.doc() for s, b in self._banks().items()},
                # plan 28 N2: a node moved on the GRAPH page; none, no part
                json.dumps(getattr(self, "layout", None) or None, sort_keys=True),
                # plan 32: a bin entry assigned or cleared
                None if self.media is None else json.dumps(self.media.to_json()))

    # ---- internals ----

    def _warn(self, name: str) -> None:
        """The strip's warning line: the load's first note — else (plan 36
        T3) that an old file was migrated to `/7` on load, until it is saved."""
        if self.notes:
            more = f" (+{len(self.notes) - 1} more)" if len(self.notes) > 1 else ""
            self.lib.say(warning=f"preset {name}: {self.notes[0]}{more}")
        elif getattr(self, "migrated", ""):
            self.lib.say(warning=f"preset {name}: {self.migrated}")

    def _landed(self, name: str | None) -> None:
        """The library's load hook: the bank lights the slot that names
        what just loaded, whichever road it came in by (the strip, an F-key,
        a file edited on disk); a preset the bank does not name lights none.
        A save lands here too: either way the preset is no longer `unsaved`."""
        self.unsaved = False
        self.lib.project.follow()
        for fn in getattr(self, "listeners", ()):
            try:
                fn(name)
            except Exception as e:  # noqa: BLE001 — a listener must not fail a load
                # the library's warning line, never `note` (the preset's own,
                # saved back into the file)
                self.lib.say(warning=f"preset listener: {type(e).__name__}: {e}"[:160])


# ---------------------------------------------------------------- factory inputs

# ---- plan 12: the party presets — one per render attraction, two hands ----
#
# Hand rows name their axis (`hand`: ``hand:right.roll``, decision
# register row 20), so they keep it on a rig that reorders or trims
# `[hands] dofs`; an axis the rig lacks leaves its row dormant. The axes
# used are the default six (hands/core.py DEFAULT_DOFS: x, y, z, roll,
# pitch, yaw), which tests/test_plan12_presets.py pins to the hands
# package. Every hand row is a `push` from the axis's own rest — a level or absent hand adds
# nothing, so the scene's bases come back when the hand leaves the box
# with or without the audit's B1 fix — except the three `position` rows
# on wrap / centred params whose base *is* the axis's rest value
# (dream.hue 0, fx.kaleido.swirl 0, lfo.1.depth 0): same rule, same
# result. docs/plans/12-presets.md is the design; the performer cards
# are docs/plans/assets/12-presets/<name>.md.
HAND_AXES = ("x", "y", "z", "roll", "pitch", "yaw")
TURN = 0.25      # a phase push's depth: ±45° across a tilt's throw


HAND_SIDES = {"L": "left", "R": "right"}
FINGERS = ("index", "middle", "ring", "pinky")    # hands/core.py PINCHES, pinned by the tests


def hand(side: str, axis: str) -> str:
    """The source address of "L"/"R"'s `axis`: ``hand:right.roll``."""
    if axis not in HAND_AXES:
        raise ValueError(f"hand axis {axis!r}: one of {', '.join(HAND_AXES)}")
    return f"hand:{HAND_SIDES[side]}.{axis}"


def pinch(side: str, finger: str) -> str:
    """The address of "L"/"R"'s thumb-to-`finger` pinch switch — a gate:
    ``hand:right.pinch.index``."""
    if finger not in FINGERS:
        raise ValueError(f"pinch finger {finger!r}: one of {', '.join(FINGERS)}")
    return f"hand:{HAND_SIDES[side]}.pinch.{finger}"


def _push(side: str, axis: str, target: str, depth: float, **kw) -> Binding:
    return Binding(hand(side, axis), target, "push", depth, **kw)


# a hand's pitch on camera.pitch: ±45° at the hand's ends. Half the 0.5 it
# was while the pitch stopped at ±1.55 — the range is a whole turn since
# 2026-10-14 (it wraps, as yaw does), and a push's depth is in norm units
PITCH_DEPTH = 0.25


def _grip_rows() -> list[Binding]:
    """The left hand holds the object: roll, pitch and yaw of the palm add
    a rigid turn (±45° at the ends of the throw — a quarter turn maps the
    cubic shapes onto themselves, so the eighth is the whole visible
    range) in the three 3D planes on top of whatever the integrator is
    doing; a level hand adds nothing and a hand that leaves springs the
    turn back over the axis's return."""
    return [_push("L", "roll", "rot.phase.XY", TURN),
            _push("L", "pitch", "rot.phase.YZ", TURN),
            _push("L", "yaw", "rot.phase.XZ", TURN)]


def _lane_rows(skip_mods: tuple[int, ...] = ()) -> list[Binding]:
    """The legacy6 band → plane and band → pattern rows, less the pattern
    inputs a hand owns in this preset (one performer per parameter)."""
    skip = {f"pattern.mod.{i}" for i in skip_mods}
    return [b for b in routing.legacy6_routes() if b.target not in skip]


def party_tumble_routes() -> list[Binding]:
    """The polytope. Left hand grips the object (3D planes); left height
    pushes the audio drive (1× → 8×: the music grips it harder). Right
    height whips the spin, reaching in deepens the 4D perspective, right
    roll and yaw add a turn in the XW and ZW planes."""
    return [*_lane_rows(), *_grip_rows(),
            _push("L", "y", "master.gain", 0.375),
            _push("R", "y", "view.speed", 0.45),
            _push("R", "z", "view.depth4", 0.35),
            _push("R", "roll", "rot.phase.XW", TURN),
            _push("R", "yaw", "rot.phase.ZW", TURN)]


def party_faces_routes() -> list[Binding]:
    """The faces. Left hand grips; left height pushes brightness (the
    faces glow, up to the 4× stop). Right height pushes the pattern mix
    in, reaching in zooms the camera onto the faces, right roll pushes
    pattern input 2 — WARP since plan 22 B1 (it was the hex cells' scale):
    rolled one way it bends the hex cells, rolled the other it leaves them
    straight, as HEX stays straight from 0 to 1; lane 2 leaves it alone —
    and fingers up tip the camera to look down onto the faces."""
    return [*_lane_rows(skip_mods=(2,)), *_grip_rows(),
            _push("L", "y", "view.bright", 0.14),
            _push("R", "y", "view.pattern_mix", 0.6),
            # 0.1892 of zoom's span: in to 7.4×, as 0.3 was before the
            # range widened to 0.005 … 200 (2026-10-21)
            _push("R", "z", "camera.zoom", -0.1892),
            _push("R", "roll", "pattern.mod.2", 0.7),
            _push("R", "pitch", "camera.pitch", PITCH_DEPTH)]


# party-field's crowd: right height from the preset's 9 copies to 69, as
# the push of 0.6 did on the count's old linear 0–100 throw — 59 detents of
# the count taper (tapers.T_INSTANCES), every one a copy below 64
FIELD_CROWD = 59 / tapers.T_INSTANCES.steps


def party_field_routes() -> list[Binding]:
    """The instance field. Right height is the crowd: more copies, the
    camera pulling back to keep them in frame and a touch more light so
    the small copies read; right roll and yaw turn every copy at once in
    XW and ZW. Left hand flies the field — sideways and reaching in pan
    it — and left height pushes how far the copies swing."""
    return [*_lane_rows(),
            _push("R", "y", "view.instances", FIELD_CROWD),
            _push("R", "y", "camera.zoom", -0.0946),   # out to 2.7×, as 0.15 was
            _push("R", "y", "view.bright", 0.1),
            _push("R", "roll", "rot.phase.XW", TURN),
            _push("R", "yaw", "rot.phase.ZW", TURN),
            _push("L", "x", "camera.pan.x", 0.1),
            _push("L", "z", "camera.pan.y", 0.1),
            _push("L", "y", "view.inst_amp", 0.5)]


def party_wake_routes() -> list[Binding]:
    """The look-back wake. Left hand grips the object — moving it is what
    paints the wake — and left height pushes the spin. Right height pushes
    the echoes in, reaching in lengthens them (a longer fade; plan 14 WP6:
    0.24 s … 1.5 s about the scene's 0.6 s), right roll positions the
    dream's hue round the whole circle (level = as painted), fingers up
    push the dream buffer's opacity."""
    return [*_lane_rows(), *_grip_rows(),
            _push("L", "y", "view.speed", 0.4),
            _push("R", "y", "dream.echo_mix", 0.45),
            _push("R", "z", "dream.fade", -0.3),
            Binding(hand("R", "roll"), "dream.hue", "position"),
            _push("R", "pitch", "dream.mix", 0.5)]


def party_tracer_routes() -> list[Binding]:
    """TRACER — the legible echoes alone (plan 14 WP6). Left hand grips
    the object — turning it is what draws the trail — and left height
    pushes the spin. Right height brightens the trail, reaching in makes
    it last longer, right roll lets the shape cover its own trail (occlude
    up) or glow through it, fingers up harden the trail to its brightest
    lines (contrast)."""
    return [*_lane_rows(), *_grip_rows(),
            _push("L", "y", "view.speed", 0.4),
            _push("R", "y", "dream.echo_mix", 0.3),
            _push("R", "z", "dream.fade", -0.3),
            _push("R", "roll", "dream.occlude", 0.6),
            _push("R", "pitch", "dream.contrast", 0.3)]


def party_tracer_values() -> dict[str, Any]:
    """The investigation's legible echo set (plan 14 §1 row 6), in
    seconds: 24 echoes one every 4 frames at 60 Hz (1/15 s — the trail
    reaches 1.6 s back), fading 0.985 a frame at 60 Hz (a half-life of
    0.76 s), echo mix 0.7, no darken, occlude 0.3, contrast 1; the
    16-cell's points and lines without faces, at speed 0.6 and brightness
    2. The dream buffer stays out (mix 0): the echoes are the look."""
    return {**party_scene(view_shape=7, view_speed=0.6, view_bright=2.0, view_depth4=2.2,
                          view_faces=False, view_points=True, view_pattern=9,
                          camera_zoom=0.9, fx_on=False,
                          **{f"view_plane.{n}": True for n in ("XW", "YW", "ZW")}),
            "dream.on": True, "dream.echoes": 24, "dream.gap": gap_of_every(4),
            "dream.fade": fade_of_decay(0.985), "dream.echo_mix": 0.7, "dream.darken": 0.0,
            "dream.occlude": 0.3, "dream.contrast": 1.0, "dream.mix": 0.0, "dream.res": 2}


def party_trip_routes() -> list[Binding]:
    """The effects. Right height fires the zoom burst, reaching in
    zooms the kaleidoscope, right roll positions its swirl (level = none),
    fingers out spread the hue cycle, fingers up flood the plasma. Left
    height positions LFO 1's depth — a quarter-note sine that pumps the
    camera zoom, so the picture beats only while the left hand is up — and
    left x / z carry the burst's centre across the frame."""
    return [*_lane_rows(),
            _push("R", "y", "fx.zoomblur.amount", 0.8),
            _push("R", "z", "fx.kaleido.zoom", -0.5),
            Binding(hand("R", "roll"), "fx.kaleido.swirl", "position"),
            _push("R", "yaw", "fx.huecycle.spread", 0.4),
            _push("R", "pitch", "fx.plasma.level", 0.4),
            Binding(hand("L", "y"), "lfo.1.depth", "position"),
            Binding("lfo:0", "camera.zoom", "push", 0.0505),   # 1.7×, as 0.08 was
            _push("L", "x", "fx.zoomblur.cx", 0.8),
            _push("L", "z", "fx.zoomblur.cy", -0.8)]


# ---- plan 14 WP5 (decision 24): the effect families on F6–F8 ----
#
# One effect family each, the effect values from the matching `library/fx`
# module preset (`fx_module`), and between them every effect in
# shaders/fx on in a party preset: ACID acid · wobble · deconverge · hue
# cycle; MANDALA plasma · kaleidoscope · fractals · glimmer; NOITA trip
# warp · trip colour · fractals · double vision. The plan-12 rules that
# hold here, and that tests/test_plan12_presets.py sweeps: six DOF, no
# pinch, every row a push from the axis's rest (the one `position` row,
# MANDALA's swirl, on a base of 0 as TRIP's), a still or absent hand is
# the scene. One plan-12 rule does not hold and no test sweeps it: NOITA
# puts a hand on two rate-type params (`fx.tripcolour.pulse`,
# `fx.warp.drift`), which plan 12 §2 kept hands off and the owner has
# since allowed (2026-10-04). The right hand plays the family's main
# effect, the left grips the object (as in tumble, faces and wake) and
# its height adds the second effect.

def fx_module(name: str) -> dict[str, Any]:
    """A `library/fx` module preset's values — what an effect preset
    takes its effect settings from (read at generation, so the module
    file stays the one place they are tuned)."""
    doc = json.loads((FACTORY / "fx" / f"{name}.json").read_text())
    return dict(doc.get("values") or {})


def party_scene(**view) -> dict[str, Any]:
    """The bases every party preset carries (plan 12 §3): the lane rows'
    bases of 1, no look-back, the effect chain on at full mix, LFO 1 at
    depth 0, then `view` — the scene's shape, planes and light, written
    with dots as underscores (``view_shape=10``, ``camera_zoom=0.8``)."""
    out: dict[str, Any] = {
        "view.speed": 0.35, "view.depth4": 2.6, "view.bright": 2.0, "view.points": False,
        "view.lines": True, "view.faces": True, "view.rotate": True,
        **{f"view.plane.{n}": False for n in PLANES},
        "view.pattern_mix": 1.0, "view.instances": 1, "view.inst_motion": 0,
        "camera.zoom": 1.0, "camera.yaw": 0.0, "camera.pitch": 0.0, "camera.pan.x": 0.0,
        "camera.pan.y": 0.0,
        "dream.on": False, "fx.on": True, "fx.mix": 1.0, "lfo.1.depth": 0.0,
        **{f"rot.rate.{n}": 1.0 for n in PLANES},
        **{f"pattern.mod.{i}": 1.0 for i in range(len(BANDS))},
    }
    for k, v in view.items():
        group, _, rest = k.partition("_")
        out[f"{group}.{rest}"] = v
    return out


def party_acid_routes() -> list[Binding]:
    """ACID — Minecraft's acid over the polytope. Right height heaves the
    frame (acid bend), reaching in tightens the rings (acid reach), right
    roll rolls it about the centre (acid twist), fingers up split the
    colours (deconverge), fingers out tighten the rainbow (hue spread).
    Left hand grips the object; its height shivers the frame (wobble)."""
    return [*_lane_rows(), *_grip_rows(),
            _push("R", "y", "fx.acid.bend", 0.6),
            _push("R", "z", "fx.acid.reach", -0.4),
            _push("R", "roll", "fx.acid.twist", 0.5),
            _push("R", "pitch", "fx.deconverge.amount", 0.6),
            _push("R", "yaw", "fx.huecycle.spread", 0.4),
            _push("L", "y", "fx.wobble.amount", 0.5)]


def party_acid_values() -> dict[str, Any]:
    """The truncated tesseract's white lines over faint rings — edges for
    the deconverge to split and the hue cycle to paint — with the `acid`
    module preset's effects, their bases where the rows push from."""
    return {**party_scene(view_shape=11, view_speed=0.3, view_bright=2.0, view_depth4=2.6,
                          view_pattern=1, view_pattern_mix=0.6, camera_zoom=1.1,
                          **{f"view_plane.{n}": True for n in ("XW", "YW", "ZW")}),
            **fx_module("acid"),
            "fx.acid.bend": 0.04, "fx.acid.twist": 0.9, "fx.acid.reach": 10.0,
            "fx.acid.breathe": 0.35, "fx.deconverge.amount": 5.0,
            "fx.wobble.amount": 0.004, "fx.huecycle.paint": 0.7, "fx.huecycle.spread": 1.2}


def party_mandala_routes() -> list[Binding]:
    """MANDALA — the plasma folded through the kaleidoscope, fractals and
    glints over it. Right height swells the fractals, reaching in folds
    the kaleidoscope tighter, right roll swirls it (position: level = no
    swirl, as TRIP), fingers up flood the plasma, fingers out grow the
    fractal lattice's cells. Left hand grips the object inside the fold;
    its height brightens the glints."""
    return [*_lane_rows(), *_grip_rows(),
            _push("R", "y", "fx.fractals.amount", 0.4),
            _push("R", "z", "fx.kaleido.zoom", -0.5),
            Binding(hand("R", "roll"), "fx.kaleido.swirl", "position"),
            _push("R", "pitch", "fx.plasma.level", 0.4),
            _push("R", "yaw", "fx.fractals.cells", -0.4),
            _push("L", "y", "fx.glimmer.amount", 0.5)]


def party_mandala_values() -> dict[str, Any]:
    """The 24-cell on plasma faces, panned off the centre so the
    eight-wedge fold rings it into a mandala, with the `mandala` module
    preset's effects. The module is a full-frame generator (it reads with
    every shape off); on the glass the black must stay black, so here the
    plasma field starts at level 0 (fingers up flood it in) and the
    fractals and glints grow only out of the shape (grounds 0)."""
    return {**party_scene(view_shape=10, view_speed=0.25, view_bright=1.6, view_depth4=2.6,
                          view_faces=True, view_pattern=9, camera_zoom=0.7,
                          **{"camera_pan.x": 190.0},
                          **{f"view_plane.{n}": True for n in ("XW", "ZW")}),
            **fx_module("mandala"),
            "fx.kaleido.zoom": 1.0, "fx.kaleido.swirl": 0.0, "fx.glimmer.amount": 1.0,
            # tuned for the glass (plan 14 WP5): a black ground
            "fx.plasma.level": 0.0, "fx.fractals.ground": 0.0, "fx.glimmer.ground": 0.0}


def party_noita_routes() -> list[Binding]:
    """NOITA — the trip stages. The scene is "heavily tripping"; right
    height is the next stage, one gesture over three params (Noita's
    stages add: the warp, the colour and the fractals toward "tripping
    balls"), reaching in makes the warp ripple finer, right roll opens the
    double vision, fingers up quicken the colour's pulse. Left hand grips
    the object; its height makes the warp's noise drift faster."""
    return [*_lane_rows(), *_grip_rows(),
            _push("R", "y", "fx.warp.amount", 0.3),
            _push("R", "y", "fx.tripcolour.amount", 0.25),
            _push("R", "y", "fx.fractals.amount", 0.2),
            _push("R", "z", "fx.warp.scale", -0.4),
            _push("R", "roll", "fx.doublevision.amount", 0.6),
            _push("R", "pitch", "fx.tripcolour.pulse", 0.4),
            _push("L", "y", "fx.warp.drift", 0.4)]


def party_noita_values() -> dict[str, Any]:
    """The 16-cell on ember faces — a warm, bright scene for the trip
    colour to swing and the fractals to glow out of — under the
    `noita-heavily-tripping` stage and Noita's drunk double vision
    (two ghosts)."""
    return {**party_scene(view_shape=7, view_speed=0.3, view_bright=1.4, view_depth4=2.4,
                          view_pattern=11, view_pattern_mix=0.8, camera_zoom=1.0,
                          **{f"view_plane.{n}": True for n in ("XW", "YW", "ZW")}),
            **fx_module("noita-heavily-tripping"),
            "fx.doublevision.on": True, "fx.doublevision.amount": 4.0,
            "fx.doublevision.ghost": 0.5, "fx.doublevision.copies": 2}


# ---- the routes-only files, full presets now (plan 13 decision 10) ----

def legacy6_values() -> dict[str, float]:
    """The bases the legacy6 routes assume: the rates on 0, where a push
    lands the reference's number (the parity anchor, tests/test_routing.py);
    the pattern inputs on 1, the pattern as designed, which the lanes push
    at the factory depth (plan 22 B3 — no longer the reference's raw out)."""
    return {**{f"rot.rate.{n}": 0.0 for n in PLANES},
            **{f"pattern.mod.{i}": 1.0 for i in range(len(BANDS))}}


def lfo_breathe_routes() -> list[Binding]:
    """The chaining demonstration (plan 09 decision 7): LFO 1 pushes
    brightness on the bar; the right hand's height positions LFO 1's depth
    — so raising the hand deepens the swell and nothing else moves; LFO 2
    pushes the fx mix on the quarter, through macro 1 as its attenuator
    (a depth subscriber of macro.1, `lfo_breathe_macros`)."""
    return [Binding("lfo:0", "view.bright", "push", 0.5),
            Binding(hand("R", "y"), "lfo.1.depth", "position"),
            Binding("lfo:1", "fx.mix", "push", 0.3)]


# the macro demo's throw (hand check 39), in fader positions: brightness
# from 1× (0.6) up to 2× (0.8); the spin from 0.25× (0.5) down to a crawl,
# about 0.06× (0.25) — one knob, two directions, over the whole throw
BREATHE_BRIGHT = (0.6, 0.8)
BREATHE_SPEED = (0.5, 0.25)


def lfo_breathe_macros() -> dict[str, Macro]:
    """Macro 1, "Breathe": LFO 2's push on the fx mix opens with it (a
    depth subscriber — was that row's `scale: macro.1`, plan 13 §2.4) while
    the picture brightens and the spin slows (two base subscribers of
    opposite polarity, plan 13 D10)."""
    return {"macro.1": Macro("Breathe", [
        Sub(depth=("lfo:1", "fx.mix"), lo=0.0, hi=1.0),
        Sub(base="view.bright", lo=BREATHE_BRIGHT[0], hi=BREATHE_BRIGHT[1]),
        Sub(base="view.speed", lo=BREATHE_SPEED[0], hi=BREATHE_SPEED[1])])}


def lfo_breathe_values() -> dict[str, Any]:
    """LFO 1 a sine at one bar, LFO 2 at a quarter, a depth the hand can
    deepen from; the Breathe knob at the bottom, so the look opens as it
    is turned up (brightness and speed at the subscribers' `from`)."""
    return {"view.bright": 1.0, "view.speed": 0.25,
            "lfo.1.sync": SYNCS.index("1 bar"), "lfo.2.sync": SYNCS.index("1/4"),
            "lfo.1.shape": SHAPES.index("sine"), "lfo.1.depth": 0.6, "macro.1": 0.0,
            # what LFO 2's swell of the fx mix swells (plan 14 WP5: the row
            # was dead with no effect on): the plasma screened under the
            # scene, from a half mix the quarter-note push breathes about
            "fx.mix": 0.5, "fx.plasma.on": True}


def lfo_breathe_desk() -> list[Binding]:
    """The factory preset layer with its own device knobs (`BREATHE_KNOBS`):
    the Breathe macro still on device knob 1 (hand check 39)."""
    return knob_desk(BREATHE_KNOBS)()


# seq-demo (plan 31 P): the drum lanes on the 8 steps of half a bar (16ths)
SEQ_DEMO_STEPS = {1: (1, 5), 2: (3, 7), 3: tuple(range(1, 9))}   # kick, snare, hats
# each lane's envelope as a one-shot drum hit, (attack, decay) in seconds:
# a punchy kick, a shorter snare, a hat that is gone before the next 16th
SEQ_DEMO_HITS = {1: (0.005, 0.30), 2: (0.005, 0.18), 3: (0.002, 0.07)}


def seq_demo_routes() -> list[Binding]:
    """The kick (env 1) pushes brightness, the snare (env 2) punches the
    zoom in, the hats (env 3) split the colours (Minecraft's deconverge,
    whose base amount is 0, so it shows only on a hat)."""
    return [Binding("env:0", "view.bright", "push", 0.5),
            Binding("env:1", "camera.zoom", "push", 0.06),
            Binding("env:2", "fx.deconverge.amount", "push", 0.5)]


def seq_demo_values() -> dict[str, Any]:
    """The pattern (`SEQ_DEMO_STEPS`) at a half-bar span and the lanes'
    envelopes one-shot (`SEQ_DEMO_HITS`, sustain 0); a dimmed picture for
    the kick to light. `seq.run` is the session's (decision 8): the pattern
    plays once the performer starts the transport."""
    from .envelope import ONE_SHOT
    from .sequencer import SPANS

    out: dict[str, Any] = {"view.bright": 0.6, "fx.mix": 1.0,
                           "fx.deconverge.amount": 0.0, "fx.deconverge.radial": 0.0,
                           "seq.span": SPANS.index("1/2 bar")}
    for lane, steps in SEQ_DEMO_STEPS.items():
        out.update({f"seq.{lane}.{k}": True for k in steps})
    for n, (attack, decay) in SEQ_DEMO_HITS.items():
        out.update({f"env.{n}.mode": ONE_SHOT, f"env.{n}.attack": attack,
                    f"env.{n}.decay": decay, f"env.{n}.sustain": 0.0})
    return out


def hands_fx_routes() -> list[Binding]:
    """Plan 08's hand-driven effect: the right hand's height positions the
    fx mix, its tilt (pitch) twists and its yaw bends the Acid shader, the left
    hand's roll pushes Acid's speed and its height the brightness."""
    return [Binding(hand("R", "y"), "fx.mix", "position"),
            Binding(hand("R", "pitch"), "fx.acid.twist", "position"),
            Binding(hand("L", "roll"), "fx.acid.speed", "push", 0.5),
            Binding(hand("L", "y"), "view.bright", "push", 0.4),
            Binding(hand("R", "yaw"), "fx.acid.bend", "position")]


def hands_pinch_routes() -> list[Binding]:
    """Plan 08's pinch gates: one hand height, two meanings by finger."""
    return [Binding(hand("R", "y"), "view.bright", "position", when=pinch("R", "index")),
            Binding(hand("R", "y"), "view.speed", "position", when=pinch("R", "middle")),
            Binding(hand("L", "y"), "fx.mix", "position", when=pinch("L", "index")),
            Binding(hand("L", "y"), "camera.zoom", "position", when=pinch("L", "middle"))]


def hands_pinch_values() -> dict[str, Any]:
    """The left index pinch's fx mix plays into the hue cycle (plan 14
    WP5: the row was dead with no effect on), from a mix of 0 — nothing
    until that pinch lifts it."""
    return {"fx.mix": 0.0, "fx.huecycle.on": True}


def hands_play_routes() -> list[Binding]:
    """Plan 08's first hand preset: the two heights and the right tilt (pitch)."""
    return [Binding(hand("R", "y"), "view.bright", "position"),
            Binding(hand("L", "y"), "view.speed", "position"),
            Binding(hand("R", "pitch"), "view.depth4", "position")]


def hands_orbit_routes() -> list[Binding]:
    """Plan 18 WP4: two hands on the camera, on the camera params and the
    axes that exist. The right hand orbits: sideways turns the camera a
    quarter turn each way, fingers up tip it to look down (±44°, as FACES).
    The left hand pans (sideways and reaching in, as FIELD) and its height
    zooms in. Every row is a push from its axis's own rest, so a level,
    low or absent hand adds nothing and the camera the mouse set stays;
    five targets, one performer each, no pinch. The hands relative to each
    other (a steering wheel) would need a derived lane and is not built
    (plan 18 fork 17). The depths are a first cut (hand check N9)."""
    return [_push("R", "x", "camera.yaw", 0.5),        # sideways: orbit, ±90°
            _push("R", "pitch", "camera.pitch", PITCH_DEPTH),  # fingers up: look down, ±45° (as FACES)
            _push("L", "x", "camera.pan.x", 0.1),      # as FIELD: fly sideways
            _push("L", "z", "camera.pan.y", 0.1),      # as FIELD: reach in
            # raise: zoom in, to 2.2× at the top. The plan's 0.3 (7.4×) put the
            # frame inside the default shape, near black (the WP4 strip).
            # 0.0757 of zoom's wider span (0.005 … 200) is the 0.12 of before
            _push("L", "y", "camera.zoom", 0.0757)]


def effects_on(routes, values: dict[str, Any],
               has: Callable[[str], bool] | None = None) -> dict[str, Any]:
    """`values` with the effects its routes drive switched on (PR #29's
    rule, for a routes-only file made a full preset): a route into
    ``fx.<name>.*`` sets ``fx.on`` and ``fx.<name>.on``, one into
    ``fx.mix`` alone sets ``fx.on``, one into the dream's own ``dream.*``
    (plan 36 T4: not a look-back's trail knob, `params.is_lookback_knob`) sets
    ``dream.on`` — each only when the file does not name it, and, with a
    registry to ask (`has`), only an id that exists. Without it every
    effect a D2 load lands would be at its default, off, and the hand
    would play into nothing."""
    out = dict(values)
    for row in routes:
        target = row.target if isinstance(row, Binding) else str(row.get("target", ""))
        parts = target.split(".")
        wants: list[str] = []
        if parts[0] == "fx" and len(parts) >= 2 and parts[1] != "on":
            wants.append("fx.on")
            if len(parts) >= 3 and parts[2] != "on":
                wants.append(f"fx.{parts[1]}.on")
        elif (parts[0] == "dream" and len(parts) >= 2 and parts[1] != "on"
              and not is_lookback_knob(target)):
            # (plan 36 T4: the dream's own knobs alone — a look-back's trail
            # knob needs no switch, and must not turn the dream on)
            wants.append("dream.on")
        for pid in wants:
            if pid not in out and (has is None or has(pid)):
                out[pid] = True
    return out


def device_knob(k: int, target: str) -> Binding:
    """Device knob `k` (1–8) on the preset layer: absolute, ring feedback —
    the row the factory map gives a knob (apc40._cc)."""
    return Binding.from_json(apc40._cc(target, apc40.DEVICE_KNOBS[k - 1], layer="preset"))


def track_fader(k: int, target: str) -> Binding:
    """Track fader `k` (S1–S8) on the preset layer (plan 24 C2): absolute,
    soft pickup, no light — the row the factory map gives a fader under
    SHIFT (apc40._cc with ring 0), on this preset's target."""
    return Binding.from_json(apc40._cc(target, apc40.CC_FADER, apc40.TRACK_FADERS[k - 1],
                                       ring=0, layer="preset"))


def _is_track_fader(b: Binding) -> bool:
    return b.kind == "cc" and b.number == apc40.CC_FADER


# plan 12 §6: the eight device knobs WAKE and TRIP put their bases on, on
# top of the factory preset layer (the band strip stays behind SHIFT)
WAKE_KNOBS = ("dream.echo_mix", "dream.fade", "dream.darken", "dream.contrast",
              "dream.occlude", "dream.mix", "dream.sat", "dream.k")
TRIP_KNOBS = ("fx.mix", "fx.plasma.level", "fx.kaleido.segments", "fx.kaleido.zoom",
              "fx.zoomblur.amount", "fx.zoomblur.glow", "fx.huecycle.paint",
              "fx.huecycle.spread")
# plan 14 WP5: the effect presets' eight, the same shape — the chain's mix
# first, then the family's bases, the hand-played ones among them
ACID_KNOBS = ("fx.mix", "fx.acid.bend", "fx.acid.twist", "fx.acid.reach",
              "fx.acid.breathe", "fx.wobble.amount", "fx.deconverge.amount",
              "fx.huecycle.spread")
MANDALA_KNOBS = ("fx.mix", "fx.plasma.level", "fx.kaleido.segments", "fx.kaleido.zoom",
                 "fx.fractals.amount", "fx.fractals.ground", "fx.glimmer.amount",
                 "fx.glimmer.ground")
# plan 14 WP6: TRACER's — the trail's six, its reach (echoes, spacing)
TRACER_KNOBS = ("dream.echo_mix", "dream.fade", "dream.echoes", "dream.gap",
                "dream.darken", "dream.contrast", "dream.occlude", "view.depth4")
NOITA_KNOBS = ("fx.mix", "fx.warp.amount", "fx.warp.scale", "fx.tripcolour.amount",
               "fx.fractals.amount", "fx.fractals.size", "fx.doublevision.amount",
               "fx.doublevision.ghost")
# plan 19 WP3: the device knobs of the three presets whose eight were dark
# (or one), each on what that preset has switched on — no knob on an effect
# that is off (fork 7). None leaves that knob dark. Every other scene-only
# preset has the fresh layer's four (apc40.SCENE)
# hands-fx: the Acid shader is its one effect; three of these a hand
# positions while it is in the box, and the knob is what they come back to
HANDS_FX_KNOBS = ("fx.mix", "fx.acid.bend", "fx.acid.twist", "fx.acid.reach",
                  "fx.acid.breathe", "fx.acid.speed", "view.depth4", "camera.yaw")
# hands-pinch: the hue cycle is its one effect, at a mix of 0 until a pinch or D1 lifts it
HANDS_PINCH_KNOBS = ("fx.mix", "fx.huecycle.paint", "fx.huecycle.spread", "view.depth4",
                     "camera.yaw", "camera.pitch", "view.pattern", None)
# lfo-breathe: Breathe stays on D1; the mix LFO 2 swells, the plasma it
# swells, LFO 1's pulse, and the scene's depth and angles
BREATHE_KNOBS = ("macro.1", "fx.mix", "fx.plasma.level", "lfo.1.depth", "view.depth4",
                 "camera.yaw", "camera.pitch", None)


def _is_device_knob(b: Binding) -> bool:
    return b.kind == "cc" and b.number in apc40.DEVICE_KNOBS


def knob_desk(targets: tuple[str | None, ...],
              faders: tuple[str | None, ...] = ()) -> Callable[[], list[Binding]]:
    """A preset layer with device knobs of its own: the factory files' desk
    (`file_desk`) **less its device knobs** (apc40.SCENE), plus device knob k + 1 on
    `targets[k]` — so no knob is mapped twice. A None leaves that knob dark.

    `faders` (plan 24 C2) is the same for the track faders: track fader
    k + 1 on `faders[k]`, a None or a missing entry dark. The factory map
    gives the faders nothing on the preset layer, so the default () adds
    no row and every factory desk is as it was (decision 23: no factory
    preset gets fader rows in this run; the sets are the owner's)."""
    # (the fader filter guards a future file_desk with fader rows; today's has none)
    return lambda: [*(b for b in file_desk() if not _is_device_knob(b)
                      and not (faders and _is_track_fader(b))),
                    *(device_knob(k + 1, t) for k, t in enumerate(targets) if t),
                    *(track_fader(k + 1, t) for k, t in enumerate(faders) if t)]


# ---------------------------------------------------------------- the generator

@dataclass(frozen=True)
class Factory:
    """What `write_factory` takes from code for one factory preset.
    `values` None: the file's values (and name, note) are data and stay;
    otherwise the whole file is generated. `desk` None: no ``desk`` key
    (the loader gives the factory preset layer)."""
    routes: Callable[[], list[Binding]]
    values: Callable[[], dict] | None = None
    name: str = ""
    note: str = ""
    macros: Callable[[], dict[str, Macro]] = dict
    desk: Callable[[], list[Binding]] | None = file_desk


def _lanes() -> list[Binding]:
    return routing.legacy6_routes()


# the house show's eight moods, whose routes are the lane rows alone
HOUSE = ("big-blue-wave", "ember-orbit", "hex-engine", "inverse-halo", "plasma-heart",
         "spiral-silk", "strobe-cage", "woven-lattice")


FACTORY_PRESETS: dict[str, Factory] = {
    # the house moods: the lane rows from code (plan 22 B3: so a change of
    # the factory depth reaches them), values and note data
    **{slug: Factory(_lanes) for slug in HOUSE},
    # plan 12's five, re-cut: routes from code, values data (WP2's)
    "party-tumble": Factory(party_tumble_routes),
    "party-faces": Factory(party_faces_routes),
    "party-field": Factory(party_field_routes),
    "party-wake": Factory(party_wake_routes, desk=knob_desk(WAKE_KNOBS)),
    "party-trip": Factory(party_trip_routes, desk=knob_desk(TRIP_KNOBS)),
    # plan 14 WP5: the three effect families on F6–F8, generated whole
    "party-acid": Factory(party_acid_routes, party_acid_values, "ACID",
                          "party-acid: Minecraft's acid over the truncated tesseract — the "
                          "frame heaves, rolls, shivers, splits its colours and cycles the "
                          "rainbow (the `acid` fx module preset)",
                          desk=knob_desk(ACID_KNOBS)),
    "party-mandala": Factory(party_mandala_routes, party_mandala_values, "MANDALA",
                             "party-mandala: plasma folded through an eight-wedge "
                             "kaleidoscope, Noita's fractals and glints over it, the 24-cell "
                             "a dim seed (the `mandala` fx module preset)",
                             desk=knob_desk(MANDALA_KNOBS)),
    "party-noita": Factory(party_noita_routes, party_noita_values, "NOITA",
                           "party-noita: Noita's trip on the 16-cell — warp, trip colour and "
                           "fractals at \"heavily tripping\", the right hand's height the "
                           "next stage, and the drunk double vision on its roll",
                           desk=knob_desk(NOITA_KNOBS)),
    # plan 14 WP6: the legible echoes, a ninth party preset (in the list,
    # on no F-key: F1–F8 are the five and the effect families)
    "party-tracer": Factory(party_tracer_routes, party_tracer_values, "TRACER",
                            "party-tracer: the 16-cell's points and lines trailing 24 echoes "
                            "over 1.6 s, each halving in 0.76 s — the look-back alone, "
                            "legible at a glance, the same on any screen",
                            desk=knob_desk(TRACER_KNOBS)),
    # the routing presets, full presets now (decision 10)
    "legacy6": Factory(_lanes, legacy6_values, "legacy6",
                       "The reference's band → plane table on bases of 0: the parity "
                       "anchor (the planes stand still until the music drives them). "
                       "The bands push the pattern inputs on 1, at the factory depth.",
                       desk=None),
    "lfo-breathe": Factory(lfo_breathe_routes, lfo_breathe_values, "lfo-breathe",
                           "The macro demo: device knob 1 is Breathe — the picture "
                           "brightens and the spin slows as the LFO's swell of the fx mix "
                           "deepens; the right hand's height deepens LFO 1's pulse.",
                           macros=lfo_breathe_macros, desk=lfo_breathe_desk),
    # plan 31 P: the step sequencer's demo, a hyperspace.preset/3 (its pattern)
    "seq-demo": Factory(seq_demo_routes, seq_demo_values, "seq-demo",
                        "The step sequencer's demo: kick, snare and hats on half a bar "
                        "drive one-shot envelopes — the kick lights the picture, the "
                        "snare punches the zoom, the hats split the colours. Press play "
                        "(the SEQ page, or seq.run): the transport is never in a preset.",
                        desk=None),
    "hands-fx": Factory(hands_fx_routes, lambda: {"fx.acid.speed": 4.0}, "hands-fx",
                        "Plan 08: both hands play the Acid shader and the fx mix.",
                        desk=knob_desk(HANDS_FX_KNOBS)),
    "hands-pinch": Factory(hands_pinch_routes, hands_pinch_values, "hands-pinch",
                           "Plan 08: a pinch picks what a hand's height moves — the left "
                           "index pinch fades the hue cycle in.",
                           desk=knob_desk(HANDS_PINCH_KNOBS)),
    "hands-play": Factory(hands_play_routes, dict, "hands-play",
                          "Plan 08: brightness, speed and 4D depth on the hands.", desk=None),
    # plan 18 WP4: two hands on the camera (in the list, on no F-key)
    "hands-orbit": Factory(hands_orbit_routes, dict, "hands-orbit",
                           "Two hands on the camera: the right hand orbits (sideways turns, "
                           "fingers up tips), the left pans (sideways, reaching in) and "
                           "zooms (height).", desk=None),
}
# the party presets, by file slug: plan 12's five and plan 14's, in the
# party show's bank order (F1–F8) and then those in no slot
PARTY = tuple(s for s in FACTORY_PRESETS if s.startswith("party-"))
# the party presets the show's F-keys load: F1–F5 plan 12's, F6–F8 the
# effect families (decision 24)
PARTY_BANK = ("party-tumble", "party-faces", "party-field", "party-wake", "party-trip",
              "party-acid", "party-mandala", "party-noita")


def generated(key: str) -> dict:
    """A code-generated factory preset (`Factory.values` set) as the
    document `write_factory` writes: its values with the effects its routes
    drive switched on, its routes, its desk (or none), its macros."""
    spec = FACTORY_PRESETS[key]
    if spec.values is None:
        raise KeyError(f"{key}: its values are data in its file")
    routes = spec.routes()
    doc: dict[str, Any] = {"schema": SCHEMA, "name": spec.name or key}
    if spec.note:
        doc["note"] = spec.note
    doc["values"] = effects_on(routes, spec.values())
    doc["routes"] = [b.to_json() for b in routes]
    if spec.desk is not None:
        doc["desk"] = desk_json(spec.desk())
    doc["macros"] = {k: m.to_json() for k, m in spec.macros().items()}
    doc["modules"] = {}
    doc["schema"] = factory_schema(doc)   # plan 31 P: seq-demo's pattern is a /3
    return doc


def write_factory(directory: Path = FACTORY_SOURCES) -> list[Path]:
    """Regenerate what the factory presets' sources take from code
    (`python -m hyperspace.preset`): the presets `FACTORY_PRESETS` gives
    values whole (`generated`); the party presets' routes, desk and
    macros; every other preset's ``desk``, the factory preset layer
    (`file_desk`). Every other key in a file — the values, the note, the
    modules — is data and stays as it is. Plan 36 T3: the sources
    (`FACTORY_SOURCES`), old files; the factory's `/7` are their
    migration (tools/migrate_library.py ``--library <sources' folder>
    --to hyperspace/library/presets``)."""
    out = []
    for key, spec in FACTORY_PRESETS.items():
        if spec.values is not None:
            path = directory / f"{key}.json"
            _write_text(path, dumps(generated(key)))
            out.append(path)
    for path in sorted(directory.glob("*.json")):
        spec = FACTORY_PRESETS.get(path.stem)
        if spec is not None and spec.values is not None:
            continue
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            raise LibraryError(f"{path.name}: {e}") from e
        if spec is not None:
            doc["routes"] = [b.to_json() for b in spec.routes()]
            doc["macros"] = {k: m.to_json() for k, m in spec.macros().items()}
        desk = file_desk if spec is None else spec.desk
        if desk is None:
            doc.pop("desk", None)
        else:
            doc["desk"] = desk_json(desk())
        path.write_text(dumps(doc))
        out.append(path)
    return sorted(out)


# ---------------------------------------------------------------- the migration
#
# Plan 13 §6, once, on the first launch of the build that has presets
# (`migrate_home`, from app.main once the library, the registry and the
# live table exist): every schema-1 project becomes presets and a
# schema-2 project; `bindings.json` gives its performer rows, preset layer,
# macros and values to them and keeps only the session's controls; every
# user routing preset becomes a full preset. A file is rewritten only
# after `routing.backup` kept it (never over any `.bak-*`; a backup that
# cannot be made leaves the file as it is); a preset is written only as a
# new file — never over a user's (a different one of that name gets a
# numbered name), and not at all where an equal one is already there.
# A second launch finds nothing to do. Every preset it writes names its
# hand lanes (decision register row 20, plan 13 WP5b): a ``hand:<i>`` row,
# gate or depth subscriber becomes ``hand:<name>`` by the layout the rig
# has at migration time (`hand_layout`), and a note says which layout.

MIGRATED = "MIGRATED"             # the preset a home with no project keeps its routes in
NOT_READ = "NOT-READ.txt"         # left in <home>/bindings/ once its files are converted
LEGACY_ROUTING = "bindings"       # the routing presets' old folder in the home


def factory_carried() -> routing.Carried:
    """What a table with no file of its own carries: the lane rows the
    factory table shipped before plan 13 WP5 (the house presets' routes)."""
    return routing.Carried(routes=[b.to_json() for b in routing.legacy6_routes()],
                           desk=None, macros={}, values={})


def hand_layout(cfg: dict | None = None) -> tuple[list[str], str]:
    """The hand lanes' names in lane order that a ``hand:<i>`` is read by,
    and which layout that is: the rig's `[hands] dofs` when `[hands]` is
    enabled (the adapter would publish exactly this), else the default
    layout (`hands.core.DEFAULTS`' dofs). The hands package is the one
    place a layout is written; it is imported here, not at the top, as the
    host imports it (app.py)."""
    from .hands.core import DEFAULTS, HandSettings, addresses, default_addresses

    if cfg and cfg.get("enabled"):
        try:
            settings = HandSettings.from_config(cfg)
        except (ValueError, TypeError, KeyError) as e:
            return default_addresses(), (f"the default layout (dofs {', '.join(DEFAULTS['dofs'])}"
                                         f"; the rig's [hands] would not build: {e})")
        dofs = [a.feature for a in settings.axes[:len(settings.axes) // 2]]
        return addresses(settings.axes), f"the rig's layout ([hands] dofs {', '.join(dofs)})"
    return default_addresses(), f"the default layout (dofs {', '.join(DEFAULTS['dofs'])})"


def live_hand_layout(router) -> tuple[list[str], str]:
    """`hand_layout` for a migration while the show runs (`Project.load`
    opening a schema-1 file): the layout the hands adapter published, else
    the default one."""
    index = (getattr(router, "names", None) or {}).get("hand")
    if index:
        lanes = [""] * (max(index.values()) + 1)
        for name, i in index.items():
            lanes[i] = name
        return lanes, "the rig's layout (as the hands adapter published it)"
    return hand_layout()


def _named_hand(addr, lanes: list[str]):
    """``hand:<i>`` as ``hand:<name>`` by `lanes`; anything else — a name
    already, another scheme, an index past the layout (dormant either
    way) — as it is."""
    if not isinstance(addr, str) or not addr.startswith("hand:"):
        return addr
    try:
        i = int(addr[5:])
    except ValueError:
        return addr
    return f"hand:{lanes[i]}" if 0 <= i < len(lanes) and lanes[i] else addr


def name_hand_rows(routes: list[dict], macros: dict, lanes: list[str]
                   ) -> tuple[list[dict], dict, int]:
    """`routes` and `macros` (files' JSON) with every numeric hand source,
    gate and depth subscriber's route named by `lanes` (`hand_layout`).
    Returns copies and how many addresses changed; idempotent — a named
    row is left as it is."""
    n = 0

    def fix(addr):
        nonlocal n
        new = _named_hand(addr, lanes)
        n += new != addr
        return new
    out = []
    for d in routes or []:
        d = dict(d)
        if "source" in d:
            d["source"] = fix(d["source"])
        if d.get("when") is not None:
            d["when"] = fix(d["when"])
        out.append(d)
    ms = copy.deepcopy(dict(macros or {}))
    for m in ms.values():
        for s in (m.get("subs") or []) if isinstance(m, dict) else []:
            dep = s.get("depth") if isinstance(s, dict) else None
            if isinstance(dep, dict) and "source" in dep:
                dep["source"] = fix(dep["source"])
    return out, ms, n


def _part(pid: str) -> str:
    """"session" for an id in a session group, else "performance" — by the
    id's prefix, so an id this build lacks is kept, not dropped."""
    return "session" if pid.partition(".")[0] in SESSION_GROUPS else "performance"


def _desk_rows(rows) -> list[dict]:
    """Carried preset-layer rows as a preset's ``desk``: no ``layer`` key
    (`desk_json`)."""
    return desk_json(Binding.from_json(d) for d in rows or [])


def _norm_rows(rows) -> list[str]:
    out = []
    for d in rows or []:
        b = Binding.from_json(d) if isinstance(d, dict) else replace(d)
        b.layer = None
        out.append(json.dumps(b.to_json(), sort_keys=True))
    return out


def same(a: dict, b: dict) -> bool:
    """Do two preset documents hold the same preset — values, routes (in
    order: the referee is first-wins), desk (as a set; no key is the
    factory preset layer) and macros? Name and note aside."""
    def desk(d):
        return sorted(_norm_rows(d["desk"] if "desk" in d else desk_json(fresh_desk())))

    def macros(d):
        return {k: m.to_json() for k, m in routing.macros_of(d.get("macros")).items()
                if not m.empty}
    try:
        return (dict(a.get("values") or {}) == dict(b.get("values") or {})
                and _norm_rows(a.get("routes")) == _norm_rows(b.get("routes"))
                and desk(a) == desk(b) and macros(a) == macros(b)
                and (media_channels.read_bins(a.get(MEDIA_KEY))[0]
                     == media_channels.read_bins(b.get(MEDIA_KEY))[0]))
    except (TypeError, KeyError, ValueError, AttributeError):
        return False


def _named(folder: Path, name: str) -> Path | None:
    """The file in `folder` a library lookup of `name` reaches: by display
    name, else by slug."""
    if not folder.is_dir():
        return None
    hit = folder / f"{slug(name)}.json"
    for p in sorted(folder.glob("*.json")):
        try:
            if json.loads(p.read_text()).get("name") == name:
                return p
        except (OSError, ValueError, AttributeError):
            continue
    return hit if hit.is_file() else None


def _held(root: Path, carried: routing.Carried) -> bool:
    """Does a user preset already hold `carried` — its routes, desk and
    macros (`same`, values aside)?"""
    want = {"routes": carried.routes, "macros": carried.macros}
    if carried.desk:
        want["desk"] = _desk_rows(carried.desk)
    folder = root / GROUP
    for p in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            doc = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and same({**doc, "values": {}}, {**want, "values": {}}):
            return True
    return False


def put_preset(root: Path, doc: dict, factory: Path = FACTORY) -> tuple[str, Path | None]:
    """Place a migrated preset in the user folder. Returns (the name the
    bank should say, the file written or None). An equal preset already
    reached by that name — the user's, else the factory's — is pointed at
    and nothing is written; a factory one that differs is shadowed by a
    new user file (what the old F-key loaded); a user file that differs is
    never touched: the preset takes the next free ``<name> 2``, ``3``, ….
    Nor is a factory preset of *another* name hidden: the library keys files
    by slug, so a user file whose slug is a factory file's shadows that
    file whole — allowed only when the two share a display name (a user
    ``party-trip`` would otherwise take TRIP off the list and the F-key)."""
    doc, _ = echo_seconds(doc)          # an old file's echo ids in seconds (plan 14 WP6)
    base = str(doc.get("name") or "PRESET")
    name, n = base, 1
    while True:
        user = _named(root / GROUP, name)
        if user is not None:
            try:
                if same(json.loads(user.read_text()), doc):
                    return name, None
            except (OSError, ValueError):
                pass
            n += 1
            name = f"{base} {n}"
            continue
        fac = _named(factory / GROUP, name)
        try:
            fac_doc = json.loads(fac.read_text()) if fac is not None else None
        except (OSError, ValueError):
            fac_doc = None
        if fac_doc is not None and same(fac_doc, doc):
            return name, None
        path = root / GROUP / f"{slug(name)}.json"
        under = factory / GROUP / path.name       # the factory file this slug would shadow
        try:
            other = under.is_file() and json.loads(under.read_text()).get("name") != name
        except (OSError, ValueError, AttributeError):
            other = True
        if path.exists() or other:              # a slug taken under another name
            n += 1
            name = f"{base} {n}"
            continue
        _write_text(path, dumps({**doc, "name": name}))
        return name, path


def slot_presets(root: Path, slots: list, carried: routing.Carried, modules: dict,
                 factory: Path = FACTORY) -> tuple[list[str | None], dict, list[str]]:
    """A schema-1 bank's inline slots as presets (`put_preset`): each
    slot's performance ids as `values` — the carried table's `values` (the
    macros' bases) filling the ids a slot lacks — the carried performer
    rows, preset layer and macros, and `modules` (the performance groups'
    labels). Returns (the bank of names, the first filled slot's session
    ids, a note per preset)."""
    bank: list[str | None] = []
    session: dict = {}
    notes: list[str] = []
    for k, slot in enumerate(slots):
        if not isinstance(slot, dict):
            bank.append(None)
            continue
        values, sess = _split_values(slot.get("values"), carried)
        if not session and sess:
            session = sess
        doc = _carried_doc(str(slot.get("name") or f"PRESET {k + 1}"), values, carried,
                           modules, note=str(slot.get("note") or ""))
        name, path = put_preset(root, doc, factory)
        bank.append(name)
        notes.append(f"slot {k + 1} → preset {name!r}"
                     + (f" ({path.name})" if path is not None else " (already there)"))
    return bank, session, notes


def _split_values(raw, carried: routing.Carried) -> tuple[dict, dict]:
    """A schema-1 snapshot's values as (the performance part, the carried
    table's `values` — the macros' bases — filling the ids it lacks; the
    session part)."""
    values: dict = {}
    sess: dict = {}
    for pid, v in dict(raw or {}).items():
        (sess if _part(pid) == "session" else values)[pid] = v
    for pid, v in carried.values.items():
        if _part(pid) == "performance":
            values.setdefault(pid, v)
    return values, sess


def _carried_doc(name: str, values: dict, carried: routing.Carried, modules: dict,
                 note: str = "") -> dict:
    """A migrated preset: `values`, and the carried table's performer rows,
    preset layer (none: no `desk` key) and macros."""
    doc: dict[str, Any] = {"schema": SCHEMA, "name": name}
    if note:
        doc["note"] = note
    doc.update(values=values, routes=copy.deepcopy(carried.routes))
    if carried.desk:
        doc["desk"] = _desk_rows(carried.desk)
    doc.update(macros=copy.deepcopy(carried.macros), modules=dict(modules))
    return doc


def _labels(modules: dict) -> tuple[dict, dict]:
    """A schema-1 project's `modules` split: (the session groups' — the
    project keeps them as they are — and the performance groups' labels,
    which go into its presets)."""
    session, perf = {}, {}
    for group, ref in dict(modules or {}).items():
        if group in SESSION_GROUPS:
            session[group] = ref
        elif group in PERFORMANCE_GROUPS and group != "macro":
            label = ref.get("name") if isinstance(ref, dict) else ref
            if label:
                perf[group] = str(label)
    return session, perf


def migrate_project(root: Path, path: Path, carried: routing.Carried, *,
                    factory: Path = FACTORY) -> tuple[list[str], bool, bool]:
    """One schema-1 project → its slots as presets and the file at
    ``hyperspace.project/2`` (kept first as ``<file>.bak-v1``). An empty
    slot points at the factory default bank's preset of that slot — what
    its F-key loaded while empty slots were seeded — unless it holds the
    project's own look (`<PROJECT> SAVED`, below), which is the startup
    whatever slot it is in. The seeds are the factory ``house`` show's (the
    factory default until plan 14 WP3). Returns (notes, whether
    a preset now holds `carried`, whether the file was rewritten); a file
    that is not schema 1 is left alone: ([], False, False)."""
    doc = json.loads(path.read_text())
    if not isinstance(doc, dict) or doc.get("schema") != PROJECT_V1:
        return [], False, False
    keep, labels = _labels(doc.get("modules") or {})
    # a schema-1 bank is the F-keys' eight: the file written holds eight
    # entries (`bank_doc`), as it did before the bank grew (plan 19 WP1)
    raw = list(doc.get("bank") or [])[:F_KEYS]
    raw += [None] * (F_KEYS - len(raw))
    bank, first, notes = slot_presets(root, raw, carried, labels, factory)
    try:
        seeds = list(json.loads((factory / PROJECTS / f"{HOUSE_PROJECT}{PROJECT_SUFFIX}")
                                .read_text()).get("bank") or [])
    except (OSError, ValueError, AttributeError):
        seeds = []
    filled = [n for n in bank if n]
    startup = filled[0] if filled else None
    pname = str(doc.get("name") or path.name[: -len(PROJECT_SUFFIX)])
    # the project's own look — the performance values it restored on open —
    # is never left only in the backup: equal to a slot's preset (as it
    # would land: the same performance values), that slot is the startup;
    # otherwise it is a preset of its own, `<PROJECT> SAVED`, the startup,
    # in the first empty slot (a full bank: in no slot, said)
    look, _ = _split_values(doc.get("values"), carried)
    own = {k: v for k, v in (doc.get("values") or {}).items() if _part(k) == "performance"}
    if own:
        match = next((bank[k] for k, s in enumerate(raw) if isinstance(s, dict)
                      and _split_values(s.get("values"), carried)[0] == look), None)
        if match is not None:
            startup = match
            notes.append(f"the project's own look is slot {bank.index(match) + 1}'s "
                         f"preset {match!r}: the startup")
        else:
            saved = _carried_doc(f"{pname.upper()} SAVED", look, carried, labels,
                                 note=f"the look project {pname!r} restored on open, "
                                      "made a preset by plan 13's migration")
            name, wrote = put_preset(root, saved, factory)
            startup = name
            empty = next((k for k, s in enumerate(raw) if not isinstance(s, dict)), None)
            if empty is not None:
                bank[empty] = name
                where = f"slot {empty + 1}"
            else:
                where = "no slot (the bank is full)"
            notes.append(f"the project's own look → preset {name!r}"
                         + (f" ({wrote.name})" if wrote is not None else " (already there)")
                         + f": the startup, in {where}")
    bank = [n if n or k >= len(seeds) else seeds[k] for k, n in enumerate(bank)]
    session = dict(doc.get("session") or {})
    for pid, v in dict(doc.get("values") or {}).items():
        if _part(pid) == "session":
            session.setdefault(pid, v)
    for pid, v in first.items():
        session.setdefault(pid, v)
    new: dict[str, Any] = {"schema": PROJECT_SCHEMA, "name": pname}
    if doc.get("note"):
        new["note"] = str(doc["note"])
    new.update(startup=startup or next((n for n in bank if n), None),
               bank=bank_doc(bank), session=session, modules=keep)
    bak = routing.backup(path, "1")
    if bak is None:
        return [*notes, f"{path.name} NOT migrated: no backup could be made"], False, False
    _write_text(path, json.dumps(new, indent=1) + "\n")
    notes.append(f"{path.name} → {PROJECT_SCHEMA} ({len(filled)} presets); "
                 f"the old file kept as {bak.name}")
    return notes, bool(filled) or startup is not None, True


def _into_default(root: Path, name: str, factory: Path = FACTORY) -> str:
    """`name` as the user show ``mine``'s startup and first slot — the show
    made from the factory ``house`` show if the user has none (until plan
    14 WP3 this was the user's ``default``, which ``library.unshadow_default``
    now renames ``mine``); an existing file is kept first (``.bak-v2``).
    The rest of the bank moves one slot along; a name pushed off the end
    keeps its file."""
    path = root / PROJECTS / f"{MINE_PROJECT}{PROJECT_SUFFIX}"
    fresh = not path.is_file()
    src = factory / PROJECTS / f"{HOUSE_PROJECT}{PROJECT_SUFFIX}" if fresh else path
    doc = json.loads(src.read_text())
    if not isinstance(doc, dict) or doc.get("schema") != PROJECT_SCHEMA:
        raise ValueError(f"{path.name} is not a {PROJECT_SCHEMA} project")
    # the bank moves one slot along over the length the file has (eight,
    # or as far as its last far slot: plan 19 WP1), so a name leaves the
    # F-keys' eight exactly as it did before the bank grew
    had = bank_doc(list(doc.get("bank") or [])[:SLOTS])
    bank = [n for n in had if n != name]
    bank.insert(0, name)
    bank += [None] * (len(had) - len(bank))
    gone = ""
    if len(bank) > len(had):
        spare = next((k for k in range(len(bank) - 1, 0, -1) if bank[k] is None), None)
        if spare is not None:
            bank.pop(spare)
        elif len(had) == F_KEYS or len(bank) > SLOTS:
            gone = f"; {bank.pop()!r} left the bank (its file stays)"
        # (a bank already past the F-keys, and full to its end, grows by one)
    doc.update(bank=bank_doc(bank), startup=name)
    if fresh:
        doc["name"] = MINE_PROJECT
        doc.pop("note", None)
        _write_text(path, json.dumps(doc, indent=1) + "\n")
        return f"{path.name}: made from the factory house show, {name!r} its startup{gone}"
    bak = routing.backup(path, "2")
    if bak is None:
        raise OSError(f"{path.name}: no backup could be made")
    _write_text(path, json.dumps(doc, indent=1) + "\n")
    return f"{path.name}: {name!r} its startup and slot 1{gone}; the old file kept as {bak.name}"


def _settled_macros(macros: dict, reg, where: str) -> tuple[dict, list[str]]:
    """A migrated file's `macros` with every base subscriber a preset may
    not carry dropped (`routing.settle_bases`: a session param, D9), each
    noted with `where` in front; the dict as it was when nothing went."""
    settled, dropped = routing.settle_bases(macros, reg)
    if not dropped:
        return macros, []
    return ({k: m.to_json() for k, m in settled.items() if not m.empty},
            [f"{where}: {n}" for n in dropped])


def migrate_routing_presets(root: Path, has: Callable[[str], bool] | None = None,
                            factory: Path = FACTORY, reg=None,
                            hands: tuple[list[str], str] | None = None, *,
                            machine: Path | None = None) -> list[str]:
    """Every user routing preset (``<machine>/bindings/*.json`` — a machine
    folder, beside bindings.json; `machine` defaults to `root`) as a full
    preset (decision 10): its values (less session ids, with the effects
    its routes drive switched on, `effects_on`), its performer rows (a
    ``scale: macro.N`` a depth subscriber; a ``hand:<i>`` named by `hands`
    — `hand_layout`'s (lanes, which layout), the default layout's when
    None — row 20), its macros (a base subscriber on a session param
    dropped with a note, D9), no ``desk`` key. The files stay where they
    are, untouched; a note beside them (NOT_READ) says they are no longer
    read, and is what makes this run once. The presets land in `root`, the
    library (plan 25)."""
    folder = (root if machine is None else machine) / LEGACY_ROUTING
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    if not files or (folder / NOT_READ).exists():
        return []
    lanes, layout = hands if hands is not None else hand_layout()
    notes: list[str] = []
    stuck = False
    for f in files:
        try:
            raw = json.loads(f.read_text())
            t = routing.Bindings.from_json(raw, desk=False)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
            notes.append(f"bindings/{f.name}: not converted ({e}); the file stays")
            continue
        routes = [b.to_json() for b in [*t.routes(), *(b for b, _ in t.dropped)]]
        values = {k: v for k, v in dict(raw.get("values") or {}).items()
                  if _part(k) == "performance"}
        macros, dropped = _settled_macros(t.macros_doc(), reg, f"bindings/{f.name}")
        notes += dropped
        routes, macros, n = name_hand_rows(routes, macros, lanes)
        if n:
            notes.append(f"bindings/{f.name}: {n} hand address(es) named by {layout}")
        doc = {"schema": SCHEMA, "name": str(raw.get("name") or f.stem),
               "note": f"the routing preset bindings/{f.name}, made a preset (plan 13 WP5)",
               "values": effects_on(routes, values, has), "routes": routes,
               "macros": macros, "modules": {}}
        try:
            name, path = put_preset(root, doc, factory)
        except (OSError, ValueError, LibraryError) as e:   # a full disk: said, retried next launch
            notes.append(f"bindings/{f.name}: NOT converted ({e}); tried again next launch")
            stuck = True
            continue
        notes.append(f"bindings/{f.name} → preset {name!r}"
                     + (f" ({path.name})" if path is not None else " (already there)"))
    if stuck:
        return notes
    try:
        _write_text(folder / NOT_READ,
                    "Plan 13 (WP5) made every routing preset in this folder a preset in "
                    "../presets/ on " + time.strftime("%Y-%m-%d") + ".\nThe app no longer "
                    "reads this folder; the files are kept as they were.\n")
    except LibraryError as e:        # a read-only folder: the next launch points at the presets again
        notes.append(f"bindings/{NOT_READ} not written ({e})")
    notes.append(f"bindings/: {len(files)} routing preset(s) are presets now; the folder "
                 f"is no longer read")
    return notes


ECHO_BACKUP = "2-frames"          # <file>.bak-v2-frames: the file before echo time went to seconds


def migrate_echo_home(root: Path) -> tuple[list[str], list[Path]]:
    """Plan 14 WP6, once per file: every user preset (``<root>/presets``)
    and look-back module preset (``<root>/dream``) that still names the
    per-frame ``dream.decay`` / ``dream.every`` rewritten in seconds
    (`echo_seconds`: 60 Hz frames, so the look is the same at 60 Hz),
    kept first as ``<file>.bak-v2-frames`` (a backup that cannot be made
    leaves the file as it is: a preset is then converted on every load by
    `Presets.load_doc`; a module preset is not — the library's module
    road reports its old ids as unknown — so the note says so). A module
    preset copied into the home after launch is converted on the next.
    Returns (the notes, the files written); nothing to do: nothing."""
    notes: list[str] = []
    written: list[Path] = []
    for group in (GROUP, "dream"):
        folder = root / group
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            try:
                text = path.read_text()
                if not any(k in text for k in LEGACY):
                    continue
                doc = json.loads(text)
            except (OSError, ValueError):
                continue
            if not isinstance(doc, dict):
                continue
            try:
                new, changed = echo_seconds(doc)
            except Exception as e:  # noqa: BLE001 — one odd hand-edited file must not stop a launch
                notes.append(f"{group}/{path.name}: NOT rewritten in seconds "
                             f"({type(e).__name__}: {e}); the file is left as it is")
                continue
            if not changed:
                continue
            if routing.backup(path, ECHO_BACKUP) is None:
                # only the presets loader converts on load; a module preset
                # lands through the library's values road, which does not
                later = ("read in seconds on every load" if group == GROUP else
                         "its fade and spacing are unknown ids until it is rewritten")
                notes.append(f"{group}/{path.name}: NOT rewritten in seconds (no backup); "
                             + later)
                continue
            try:
                _write_text(path, dumps(new) if group == GROUP
                            else json.dumps(new, indent=1, ensure_ascii=False) + "\n")
            except LibraryError as e:
                notes.append(f"{group}/{path.name}: NOT rewritten ({e})")
                continue
            written.append(path)
            notes.append(f"{group}/{path.name}: look-back in seconds ({'; '.join(changed)})")
    return notes, written


def migrate_home(lib, router, hands_cfg: dict | None = None) -> list[str]:
    """Plan 13 §6's one-time migration of the library home (see above):
    the schema-1 projects, the user routing presets, then `bindings.json`
    — its preset part (`Bindings.carried`) into the presets first (a
    ``MIGRATED`` preset when no project took it), and only then the file
    rewritten with the session's controls. Every hand lane a preset it
    writes names by number is named by `hands_cfg` — the config's
    ``[hands]`` section: the rig's layout when enabled, else the default
    (`hand_layout`, decision register row 20). A converted ``default``
    show becomes ``mine`` (library.unshadow_default), and ``MIGRATED``
    goes on its slot 1. Re-opens the launch's show (the last opened, else
    the party) when a show changed. Every note goes to stderr and the sum to
    `lib.warning`; returns the notes. Nothing to do: nothing written.

    Documents (shows, presets) are read and written in the library root
    (`lib.home`); bindings.json (the router's table) and the legacy
    ``bindings/`` folder are machine files, read from `lib.machine` (plan
    25). A shared library that is missing (D5): nothing at all."""
    if getattr(lib, "missing", None) is not None:
        return []
    root, table = lib.home, router.table
    machine = getattr(lib, "machine", root)
    reg = lib.reg
    factory = lib.factory
    carried = table.carried
    use = carried if carried is not None else factory_carried()
    notes: list[str] = []
    # a base subscriber on a session param goes before any preset is made
    # from the table's macros (D9)
    use.macros, dropped = _settled_macros(use.macros, reg, "bindings.json")
    notes += dropped
    # and every hand lane by name, before any preset is made from its rows
    hands = hand_layout(hands_cfg)
    use.routes, use.macros, n = name_hand_rows(use.routes, use.macros, hands[0])
    if n:
        notes.append(f"bindings.json: {n} hand address(es) named by {hands[1]}")
    written: list[Path] = []
    held = False                          # a preset now holds `carried`
    stuck = False                         # a schema-1 project left as it was
    projects = False
    for path in sorted((root / PROJECTS).glob(f"*{PROJECT_SUFFIX}")):
        try:
            got, took, rewrote = migrate_project(root, path, use, factory=factory)
        except (OSError, ValueError, LibraryError) as e:
            notes.append(f"{path.name}: NOT migrated ({e})")
            stuck = True
            continue
        notes += got
        held = held or took
        stuck = stuck or (bool(got) and not rewrote)
        if rewrote:
            projects = True
            written.append(path)
    # a `default` show just converted from schema 1 becomes `mine` now,
    # as the launch's Library did for one plan 13 converted before
    # (decision 22) — before MIGRATED goes into `mine`
    if projects:
        renamed = lib.unshadow()
        notes += renamed
        written += [root / PROJECTS / f"{MINE_PROJECT}{PROJECT_SUFFIX}"] if renamed else []
    notes += migrate_routing_presets(root, (lambda pid: pid in reg) if reg is not None
                                     else None, factory, reg, hands, machine=machine)
    # a user preset already holding the table's part (a launch that
    # converted the projects but could not rewrite bindings.json, or a
    # MIGRATED preset made before) takes it: no second MIGRATED, and the
    # default project is not touched again
    if carried is not None and not carried.empty and not held and _held(root, carried):
        held = True
        notes.append("bindings.json's routes, desk and macros are already in a preset")
    # no project took the table's part: a MIGRATED preset keeps it — unless
    # a schema-1 project could not be converted, whose next try will
    if carried is not None and not carried.empty and not held and not stuck:
        values = {k: v for k, v in (reg.snapshot(part="performance") if reg else {}).items()}
        values.update({k: v for k, v in carried.values.items() if _part(k) == "performance"})
        doc: dict[str, Any] = {"schema": SCHEMA, "name": MIGRATED,
                               "note": "bindings.json's routes, desk and macros, kept by "
                                       "plan 13's migration", "values": values,
                               "routes": carried.routes}
        if carried.desk:
            doc["desk"] = _desk_rows(carried.desk)
        doc.update(macros=carried.macros, modules={})
        try:
            name, path = put_preset(root, doc, factory)
            notes.append(f"bindings.json's routes, desk and macros → preset {name!r}"
                         + (f" ({path.name})" if path is not None else " (already there)"))
            notes.append(_into_default(root, name, factory))
            projects = True
            written.append(root / PROJECTS / f"{MINE_PROJECT}{PROJECT_SUFFIX}")
            held = True
        except (OSError, ValueError, LibraryError) as e:
            notes.append(f"bindings.json's routes NOT moved ({e}); the file is left as it is")
    if carried is not None and table.path is not None and (held or carried.empty):
        # no file yet (an old midi_map.json's rows, carried): nothing to keep
        fresh = not table.path.exists()
        bak = None if fresh else routing.backup(table.path, table.read_at)
        kept = "" if fresh else f"; the old file kept as {bak.name}" if bak else ""
        if table.notes:          # after the backup: what it says is what happened
            table.announce(table.path, written=fresh or bak is not None, kept=bak)
        if bak is None and not fresh:
            # no backup, no rewrite (plan 19 fork 12) — and no later write
            # either until the copy is made (`Bindings.write` retries it)
            table.unbacked, table.error = table.read_at, routing.NOT_REWRITTEN
            table.said = table.said or (f"{table.path.name} NOT rewritten: no backup could "
                                        "be made")
            notes.append("bindings.json NOT rewritten: no backup could be made")
        else:
            table.write()
            if table.error:
                notes.append(f"bindings.json NOT written ({table.error}){kept}")
            else:
                table.carried = None
                notes.append(f"bindings.json now holds only the session's controls{kept}")
                written.append(table.path)
    # plan 14 WP6: echo time in seconds — last, so a preset written above
    # from an old file is converted too
    echo_notes, echo_written = migrate_echo_home(root)
    notes += echo_notes
    written += echo_written
    if written:
        lib._sync(*written)
    if projects:
        lib._open_default()
        lib.report(lib.project._apply(), lib.project.name)
    for n in notes:
        print(f"migrate: {n}", file=sys.stderr)
    if notes:
        what = "plan 13 migration" if len(notes) > len(echo_notes) else "echo time in seconds"
        lib.say(warning=f"{what}: {len(written)} file(s) rewritten, backups beside "
                        "them — the details are on stderr")
    return notes


if __name__ == "__main__":
    for p in write_factory():
        print(p, file=sys.stdout)
