"""The preset — one file that holds everything a performance moment is
(plan 13 D1, §2.1): ``hyperspace.preset/2``.

  {"schema": "hyperspace.preset/2", "name": "TRIP", "note": "…",
   "values": {id: base, …},            the performance part (params.PARTS)
   "routes": [row, …],                 the performer rows (routing.Binding)
   "desk":   [row, …],                 the APC40's preset layer (routing.Binding)
   "macros": {"macro.1": {…}, …}}     the macros' labels and subscribers

(plan 44 D3, ``/10``: the module labels ``modules`` and plan 24 C3's
``desk_template`` are retired — a load of an older file drops both,
`graphmigrate.ten` — and ``"bus": {"cut": [{"from", "to"}, …]}`` is the
preset's bus cuts, `BUS_KEY`, below.)

(plan 32 S: a ``media`` section holds the channels' bins:
``{"channels": {"a": ["shared:loops/tunnel.mp4", null, …], …}}``.)

**The schema a save writes** (row 394, the owner's decision of
2026-10-25, superseding D1's ladder, R10 and R15): always the newest,
``hyperspace.preset/10`` (`SAVE_SCHEMA`, plan 44 D3; ``/9`` was plan 43
C2's, row 521 closed: no ``/7``-or-``/8`` fork), in today's words — the wired frame (plan 35) that
says everything (plan 36 W3: every edge a wire, the hands entries and
`laid` written, effects only where the section names them), today's node
ids and canvas ids, every value the registry holds (the media family, the
envelopes and the sequencer, the eye), the groups where there are any,
the spin's pose, no retired id written back. Both Macs run the same
build, so nothing is written for an older one. A ``/7`` or ``/8`` is read
as it is — one with no graph section is black — but for the eye, which
it never named (`graphmigrate.nine`: the open show's, else the build's).
Every older schema (`VERSIONS`) is read only through the one-way
migration to ``/7`` (`graphmigrate.seven`), with a note: ``/2`` is the
format above, ``/3`` adds the envelopes and the sequencer (plan 31),
``/4`` media (plan 32), ``/5`` the free graph (plan 33), ``/6`` the wired
frame (plan 35), ``/8`` the groups (plan 40), ``/9`` the one orbit camera
(plan 43 C2), ``/10`` the look made whole (plan 44 D3: the hands' and
clouds' looks in ``values``, the bus cuts in ``bus``, read from the open
show for an older file — `graphmigrate.ten`); a re-save is ``/10``.
tools/migrate_library.py rewrites a library's presets that way, once.

**The look made whole** (plan 44 D3, plan 43 §6): the hands' look
(``ghost.*`` but ``ghost.mirror``, the room's) and the clouds'
(``cloud.*``) are performance params, saved and landed like any value;
and the **bus cuts** — which of the rig's cables from All outputs into a
window this preset cuts (`graph.RigWires`, plan 36 T1's ``rig``, once
the show's) — are `Presets.bus`: read from ``bus`` by a load (none: every
cable stands), written by a save when any is cut, in the dirty dot and
in a load's undo step, and what the renderer reads (`rig_source` is the
presets, `graph.rig_of` reads `rig`).

**The one orbit camera** (plan 43 C2, the owner, 2026-11-02): a preset
is a complete look, so the camera is all of it — `camera.*` (the shape's
pose and scale in the world) and `eye.*` (the eye it is seen through),
landed like any value — and the **spin's pose**: every save writes the
six `rot.phase.*` (`params.POSE_IDS`) under ``"pose"`` (`POSE_KEY`, beside
``values``, which stays the bases: a phase is no base), `view.body`
folded in (`ViewState.pose`), and a load **sets** the turn there
(`set_pose`), so the same preset opens on the same turn. A file with no pose (every file
before ``/9``, and every file the migration rewrote: `headless.resave`)
leaves the turn spinning, as it always did.

One file per preset, ``<library>/presets/<slug>.json`` — one tier, every
preset the user's (2026-10-28: nothing ships, nothing is "factory", nothing
is hidden). `Presets` registers the folder with the library as a
**document kind** (`Library.kind`), so listing, load / save as / delete /
rename, the dirty dot and the file watch are the library's, and the
PRESETS page (ui_presets.py: the strip over ``presets`` and the list)
drives it. The bank — the desk's pads, F1–F8 — names these files; the
project holds the bank (library.Project, ``hyperspace.project/2``). Since
plan 13 WP5 it is the only kind: the routing presets are presets now.

A load is a scene-setter (docs/ARCHITECTURE.md §3): it writes bases and
replaces rows, never an offset. In order (plan 13 §5):

1. note what the file names that a preset may not: a session param
   ("`tempo.bpm` is the session's, ignored"), an id nobody has, a
   ``routes`` row that is not a performer row or that aims at a param
   that is not modulatable (dropped), a second performer on one target
   (the referee's, below);
2. land the values: **every** persisted param of every performance group
   gets the file's value or the value its object was built with
   (`Library._fresh_of` — never a group's ``default.json``, plan 44 D3),
   in registry order, in one go (D2). A session param is never touched. The rotation
   phases (not persisted) are set to the file's pose when it has one
   (plan 43 C2), else left spinning;
3. replace every performer row with ``routes`` (`Bindings.set_routes`;
   the referee is first-wins, the rest in ``table.dropped`` for the
   ROUTING page);
4. replace the desk's preset layer with ``desk`` (`Bindings.set_desk`: a
   row on an invariant control is dropped and its note joins step 1's;
   the desk drops to the preset layer, D4, and the MIDI adapter redraws
   every ring and LED with the faders' catch cleared). A file with **no**
   ``desk`` key gets the default preset layer (`routing.factory_desk`'s
   preset rows — a fresh preset, plan 13 §3.2); ``"desk": []`` is an
   empty preset layer, every preset control dark (D8);
5. replace the macros' labels and subscribers with ``macros``
   (`Bindings.set_macros`: a base subscriber on anything but a
   performance param — a session one, D9 — is dropped and its note joins
   step 1's) and land the base subscribers at once from the macros' bases
   just landed (`Router.follow_macros(force=True)`). The macro is the
   scene-setter of record: a param a base subscriber names ends at the
   subscriber's value even when ``values`` names it too;
6. each performance group's strip is clean against the values just
   landed, naming no module preset (plan 44 D3: the ``modules`` labels
   are retired, row 540);
7. the notes from step 1 are kept in ``notes`` and summed up in
   ``Library.warning`` for the panel.

A save (`document`) writes the performance snapshot, every performer row
(disabled ones too), the table's preset-layer rows (`Bindings.desk`, a
row's ``layer`` left out: every desk row is the preset's), the table's
macros (`Bindings.macros_doc`) and the bus cuts. The dirty dot (`signature`) covers all of it, so a Learn,
an Unbind or a ROUTING-page edit — which change the table and write no
file — shows as the loaded preset edited; only a save (⇧F, a pad, the
strip's save / as…) writes it.

The twenty-five presets the build once shipped, and the generator that
made them, left the app on 2026-10-28 (one tier). The files live on as
the golden frames' corpus (tests/corpus/presets/, tools/golden_frames.py),
their old-schema sources beside the tests (tests/fixtures/factory-sources/)
as the migration tests' inputs — neither is read by the app. Plan 13 §6's
one-time home migration (schema-1 shows, routing presets, an old
bindings.json's preset part) went with them: both Macs are long past it.
"""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import apc40, graphmigrate, graphview, modifiers, patches, routing, undo
from .fx import declare as declare_fx
from .ghost import GhostState
from .ghost import prefix as ghost_prefix
from .ghost import register as declare_ghost
from .graph import (
    EMPTY,
    FRAME_KEY,
    WIRED_FRAME,
    GraphError,
    GraphSpec,
    RigWires,
    Wiring,
    read_graph,
)
from .library import (
    PERFORMANCE_SCHEMA,
    PRESETS,
    RETIRED_MODULES,
    read_positions,
)
from .lookback import (
    LEGACY,
    fade_depth,
    migrate_row,
    migrate_values,
)
from .media import channels as media_channels
from .modifiers import Modifier
from .palettecompat import palette_slice
from .params import (  # noqa: F401 — pan_world, UNITS…: re-exported, preset.* names
    CUT_GROUP,
    MATTE_GROUP,
    PAN_IDS,
    PERFORMANCE_GROUPS,
    PLANES,
    POSE_IDS,
    RESIZE_GROUP,
    SEGMENT_GROUP,
    SESSION_GROUPS,
    SWITCH_GROUP,
    UNITS,
    UNITS_KEY,
    declare_cuts,
    declare_lookbacks,
    declare_mattes,
    declare_resizes,
    declare_segments,
    declare_switches,
    fx_files,
    is_cut_id,
    is_instance_id,
    is_lookback_id,
    is_lookback_knob,
    is_matte_id,
    is_resize_id,
    is_segment_id,
    is_switch_id,
    pan_world,
    part_of,
    retaper_depths,
)
from .routing import MOD_OPS, Binding, is_continuous

SCHEMA = PERFORMANCE_SCHEMA
# the schemas a load reads (each migrated on load; row 394: a save writes
# `SAVE_SCHEMA` only). /3 is /2 plus the envelopes and the sequencer (plan
# 31 P), /4 /3 plus media (plan 32 S, D1), /5 /4 plus the free graph (plan
# 33 M), /6 /5 with the wired frame in the new ids (plan 35, row 385)
SCHEMA_V3 = f"{SCHEMA.rpartition('/')[0]}/3"
MEDIA_SCHEMA = f"{SCHEMA.rpartition('/')[0]}/4"
FREE_SCHEMA = graphmigrate.FREE_SCHEMA
WIRED_SCHEMA = graphmigrate.WIRED_SCHEMA
# plan 40 T2 (D4, D7): `/8` is `/7` plus `groups` — what a save wrote while
# the preset held a group, until plan 43 C2 made every save `/9` (row 576)
GROUPS_SCHEMA = graphmigrate.GROUPS_SCHEMA
# plan 43 C2 (rows 572, 576): `/9` is `/8` with the eye and the pose — what
# every save writes, groups or none
EYE_SCHEMA = graphmigrate.EYE_SCHEMA
# plan 44 D3 (rows 611–625): `/10` is `/9` with the look made whole — the
# hands' and clouds' looks in `values`, the bus cuts in `bus`, no module
# labels, no desk template — what every save writes
LOOK_SCHEMA = SAVE_SCHEMA = graphmigrate.LOOK_SCHEMA
VERSIONS = (2, 3, 4, 5, 6, 7, 8, 9, 10)
# plan 44 D3: the preset's bus cuts, `{"cut": [{"from", "to"}, …]}` — the
# rig's cables from All outputs into a window that this preset cuts
# (`graph.RigWires`); no key: every cable stands
BUS_KEY = graphmigrate.BUS_KEY
# what a load says of a file naming a desk template (retired, plan 44 D3;
# said by the one ladder since plan 50)
TEMPLATE_RETIRED = graphmigrate.TEMPLATE_RETIRED
# plan 43 C2 (row 573): the spin's pose, `{"rot.phase.XY": angle, …}` — the
# six `POSE_IDS` in radians — beside `values` (a phase moves every frame: it
# is no base, so `values` stays the bases' snapshot)
POSE_KEY = "pose"
# what a load says of a pose it could not read (six numbers, by `POSE_IDS`)
POSE_UNREAD = "pose: not six numbers, ignored — the turn is left spinning"
# the registry groups (and lane schemes) a /2 file never names
V3_GROUPS = ("env", "seq")
# the preset keys a bank writes only off its default (modbank, plan 31 B)
V3_KEYS = ("lfos", "envs")
GROUP = PRESETS                   # the library folder, and the strip's group
# plan 35 T7 (row 387): the new preset — what the strip's `new` chip starts,
# named until it is saved, and what it says
UNTITLED_PRESET = "untitled"
NEW_SAID = "new preset: default values, shape → scene → All outputs — a shape on every window"
# plan 36 T3 (W3): a `/7` with no graph section, or an empty one — the strip says so
NO_GRAPH_SAID = "no graph: nothing is wired — black until something is wired to an output"
# … and one whose section is not a wired frame (no `"frame": "wired"`)
UNWIRED_SAID = ("graph: a /7 section is a wired frame (\"frame\": \"wired\"); this one is "
                "not read — black")

# plan 32 S (row 337): the media section
MEDIA_KEY = "media"
BMP_PREFIX = "view.bmp_"          # the one bitmap file's params, gone in plan 32


# the largest saved angle: π rounded *down* to the file's six places, so a
# written angle is always strictly inside (−π, π) and reads back as itself
POSE_EDGE = math.floor(math.pi * 1e6) / 1e6


def pose_angle(a: float) -> float:
    """One angle of `ViewState.pose` as a pose saves it (plan 43 C2, review
    1): rounded to six places, and — an angle on the folded roads, inside
    [−π, π] — held to ±`POSE_EDGE`: π itself would round to 3.141593 > π,
    fold to −π on the next save and write −3.141593, so save → load → save
    would not be a fixed point. A scene's unfolded angle (its layers spin
    at fractions of it, `ViewState.pose`) is only rounded: it is never
    folded, so its rounding is its fixed point. Every value this returns
    is its own rounding."""
    a = float(a)
    r = round(a, 6)
    if -math.pi <= a <= math.pi:
        r = min(max(r, -POSE_EDGE), POSE_EDGE)
    return r + 0.0


def read_pose(pose: Any) -> list[float] | None:
    """A file's pose section (plan 43 C2, row 573): its six `rot.phase.*`
    angles in `POSE_IDS` order, each a finite number — else None (no pose,
    or not all of one: the load says so and leaves the turn spinning)."""
    if not isinstance(pose, dict):
        return None
    out: list[float] = []
    for pid in POSE_IDS:
        v = pose.get(pid)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            return None
        out.append(float(v))
    return out


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
    """A fresh preset's desk: the default map's preset layer (plan 13 §3.2)
    — what a file with no ``desk`` key gets. It holds
    no track fader (plan 24 C2: the faders are a preset's own targets, with
    no inherited default), so a fresh preset leaves S1–S8 dark; a fader row
    a preset's desk holds (`track_fader`) loads, saves and lights like a
    knob's."""
    return [b for b in routing.factory_desk(profile) if b.layer == "preset"]


# ---- the render graph (plan 26 A4) ----

GRAPH_KEY = "graph"
FX_GROUP = "fx"          # the effects' param group (plan 40 T5: no module presets since D6)


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
      preset's, like `ghost.*`, its values in the preset's `values` — but
      `ghost.2.mirror`, the room's, which the open show keeps — on a
      `GhostState` of its own that is kept while the app runs); and (plan 33
      S) each switch's `switch[.n].select` (`params.declare_switches`: a
      performance param, its pick in the preset's `values`); and (plan
      34 Z) each resize's `resize[.n].*` (`params.declare_resizes`, by its
      entry, reached or not); and (plan 39 T2) each matte's `matte[.n].*`
      (`params.declare_mattes`, likewise); and (plan 39 T3) each cut's
      `cut[.n].*` (`params.declare_cuts`, likewise); and (plan 39 T4) each
      segment's `segment[.n].*` (`params.declare_segments`, likewise);
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
        # plan 38 B3: the hold, while the projector is held (`hold.Hold`,
        # duck-typed: `keep(kind, names)`, `reset_delays()`) — every landing
        # keeps the held program's nodes too; None: a landing is exactly
        # its graph
        self.hold = None
        # 2026-11-02 (G0, row 563): told after every landing — `Presets`
        # points it at `settle_groups`, so a group's member list loses a
        # deleted node in the same operation, never on the next draw or save
        self.on_land: Callable[[], None] | None = None
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
        wired frame, and that is what a save writes (row 394: `/7`, plan 36
        T3; `/9` since plan 43 C2).

        An extra hands node declared for the first time this run takes
        its room setting (`ghost.2.mirror`, the session's) from the open
        show; its look is the preset's values (plan 44 D3)."""
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
        self._settle(spec)
        self.spec, self.doc = spec, copy.deepcopy(doc)
        self.free = copy.deepcopy(free)
        self._push()
        if self.on_land is not None:
            self.on_land()

    def names(self, spec: GraphSpec | None = None) -> dict[str, Any]:
        """The node instances `spec` (the landed one by default) declares,
        by kind — what a landing settles: ``fx`` (the effect instances that
        exist, `FxState.held`'s word: None for every file), ``switch``,
        ``resize``, ``lookback``, and (plan 39 T2–T4) ``matte``, ``cut``,
        ``segment``. Plan 38 B3: what a hold keeps."""
        spec = self.spec if spec is None else spec
        if spec is None:
            fx = getattr(self.fx, "held", None) if self.fx is not None else frozenset()
            return {"fx": fx, "switch": [], "resize": [], "lookback": [],
                    "matte": [], "cut": [], "segment": []}
        return {"fx": frozenset(spec.effect_names()),
                "switch": [sw.name for sw in spec.switches],
                "resize": [z.name for z in spec.resizes],
                "lookback": [lb.name for lb in spec.lookbacks],
                # plan 39 T2–T4: the mattes, cuts and segments, by their entries
                "matte": [m.name for m in spec.mattes],
                "cut": [c.name for c in spec.cuts],
                "segment": [x.name for x in spec.segments]}

    def settle(self) -> None:
        """Settle the instances to the landed graph again (plan 38 B3: at
        Take, once the hold no longer keeps the program's — the live set
        wins: what only the program had goes)."""
        self._settle(self.spec)

    def _settle(self, spec: GraphSpec | None) -> None:
        """Declare `spec`'s instances and drop the others' — each kind's
        names through the hold's `keep` while the projector is held (plan
        38 B3: the program's effects, switch picks, resizes and look-backs
        — and plan 39's mattes, cuts and segments — stay, with their
        values, phases and states, until Take or Drop)."""
        reg, names = self.reg, self.names(spec) if spec is not None else {
            "fx": frozenset(), "switch": [], "resize": [], "lookback": [],
            "matte": [], "cut": [], "segment": []}
        hold = getattr(self, "hold", None)
        if hold is not None:
            names = {kind: hold.keep(kind, n) for kind, n in names.items()}
        if self.fx is not None:
            # plan 36 T3 (W3): the effects the section names, and no others
            changed = self.fx.hold(names["fx"])
            if changed:
                declare_fx(reg, self.fx, changed)
        # plan 33 S: each switch's `select`, as the effect instances' params
        declare_switches(reg, names["switch"])
        # plan 34 Z: each resize's values, by its entry — reached or not, so
        # an unwired resize keeps its knobs as an unwired switch its pick
        declare_resizes(reg, names["resize"])
        # plan 39 T2: each matte's values, by its entry, as a resize's
        declare_mattes(reg, names["matte"])
        # plan 39 T3: each cut's values, by its entry, as a matte's
        declare_cuts(reg, names["cut"])
        # plan 39 T4: each segment's values, by its entry, as a cut's
        declare_segments(reg, names["segment"])
        # plan 36 T4: each extra look-back's own ring and trail, by its entry
        declare_lookbacks(reg, names["lookback"])

    def free_doc(self) -> dict | None:
        """The section in the free graph's words (plan 33 M; plan 35 T3: the
        wired frame every load lands): what a save writes (row 394: always
        `/7`) — `free` when the load kept the file's section beside it,
        else `doc`."""
        free = getattr(self, "free", None)      # (a section from before a hot reload)
        return free if free is not None else self.doc

    def _seed(self, name: str) -> None:
        """A newly declared hands node's session params (plan 44 D3: its
        mirror, `params.SESSION_KEYS`; its look is the preset's) from the
        open show's session, where it holds them (`library.Project.session`)
        — once per show opened (`Project.opened`): after that the node's
        kept state is the live one."""
        project = getattr(getattr(self, "lib", None), "project", None)
        seeded = self.__dict__.setdefault("_seeded", {})
        show = getattr(project, "opened", None)
        if name in seeded and seeded[name] == show:
            return
        seeded[name] = show
        session = getattr(project, "session", None) or {}
        held = {pid: v for pid, v in session.items()
                if pid.startswith(name + ".") and pid in self.reg
                and part_of(self.reg[pid]) == "session"}
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
        (plan 36 T3) which effect instances exist (`FxState.held`). Plan 38
        B3: while the projector is held, the landed graph's own instances —
        not those kept for the program, which an undo after Take must not
        bring back onto a graph that lacks them (unheld the two are one)."""
        held = getattr(self.fx, "held", None)
        if getattr(self, "hold", None) is not None and self.spec is not None:
            held = frozenset(self.spec.effect_names())
        return (self.spec, copy.deepcopy(self.doc), copy.deepcopy(getattr(self, "free", None)),
                held)

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
        held = mark[3] if len(mark) > 3 else None
        hold = getattr(self, "hold", None)
        if hold is not None and len(mark) > 3:          # plan 38 B3: an undo while held
            held = hold.keep("fx", held)
        if len(mark) > 3 and fx is not None and getattr(fx, "held", None) != held:
            changed = fx.hold(held)
            if changed:
                declare_fx(self.reg, fx, changed)

    def _push(self) -> None:
        r = self.renderer
        if r is None:
            return
        r.wiring = self.wiring
        r.ghost_states = {name: self.states[name] for name in sorted(self.declared)}


# plan 28 N1: the preset's modifier nodes (`modifiers.Modifier`), a list of
# entries after `routes` — ``{"id": "mod.1", "kind": "smooth", "in":
# ["hand:right.energy"], "attack": 0.05, "release": 0.6}``. No schema bump:
# an older build ignores the key (and a route on a ``mod:`` lane is a
# dormant row there)
MODIFIERS_KEY = "modifiers"
# plan 28 N2: where the GRAPH page's nodes the look holds sit (the
# modifiers, the macros, the render nodes and their params) —
# ``{"<node id>": [x, y]}``, written after everything else, one node a
# line; the rig's nodes are the show's (library.LAYOUT). No key: laid out
# automatically, no note and no dirt. An older build ignores the key
LAYOUT_KEY = "layout"
# plan 40 T2 (P2, D4, D7): the GRAPH page's groups — a fold of the canvas
# and a list in the file, never a node of the renderer (`build_graph`, the
# signature and the goldens see the flat graph) — ``[{"id": "group.1",
# "name": "acid wash", "patch": "acid-wash", "nodes": ["render:acid.2",
# "mod.3"], "open": false}]``, written after `layout`, only when there is
# one (then the file is `/8`). `patch` is provenance (the slug it was
# spawned from), never re-read; a group's position is its members'
GROUPS_KEY = graphmigrate.GROUPS_KEY
GROUP_NAME = "group {n}"
GROUP_GONE = "group {name}: {node} is not in the preset — left out"
GROUP_REFUSED = "group {name}: {why}"
GROUP_EMPTY = "group {name}: nothing of it is in the preset — left out"
GROUP_TWICE = "group {name}: {node} is in group {other} already — left out"
GROUP_BAD = "groups: an entry that is not a group, ignored"
# the performance groups with no module presets: a macro's meaning is its
# subscribers and a modifier's params are its entry, both the preset's
# (plan 33 S: a switch's pick means nothing without the preset's graph;
# plan 34 Z: nor a resize's values; plan 39 T2: nor a matte's; T3: nor a cut's)
# (T4: nor a segment's) — and (plan 40 T5, D6) the effects', whose module
# presets are retired outright: a save writes no fx label
NO_MODULE = ("macro", modifiers.GROUP, SWITCH_GROUP, RESIZE_GROUP, MATTE_GROUP, CUT_GROUP,
             SEGMENT_GROUP, FX_GROUP)
# the groups whose module presets are retired (plan 40 T5, D6,
# `library.RETIRED_MODULES`): a file that still names one keeps the label
# on load, quietly — it never loaded anything (D3) — and the next save
# drops it (`NO_MODULE`)


group_number = graphmigrate.group_number    # `group.3` → 3 (the one rule, GRAPH's too)


def group_entry(g: dict) -> dict:
    """A group's entry in the file's key order: id, name, patch (when it
    has one), nodes, open — and `kept_by_host` (plan 40 T3's rows a spawn's
    conflict sheet gave the preset) when present."""
    out = {"id": g["id"], "name": g["name"]}
    if g.get("patch"):
        out["patch"] = g["patch"]
    out["nodes"] = list(g["nodes"])
    out["open"] = bool(g.get("open"))
    if g.get("kept_by_host"):
        out["kept_by_host"] = copy.deepcopy(list(g["kept_by_host"]))
    return out


def read_groups(raw, held, refusal: Callable[[list[str]], tuple[set, list[str]]] | None = None
                ) -> tuple[list[dict], list[str]]:
    """A file's `groups` (plan 40 T2, load step 6½) → (the groups, the
    notes). A member id the preset does not hold (`held`, the canvas ids
    its graph, modifiers and voices make) is left out with a note ("group
    acid wash: acid.3 is not in the preset — left out"); one a group may
    not hold (`refusal(ids)` → (the ids kept, the words for the rest):
    `patches.groupable`'s rule, plan 50) is left out in its words; a node already in an
    earlier group is left out of the later; a group left with no member is
    dropped, said; an entry that is not a group is ignored, said. Pure."""
    groups: list[dict] = []
    notes: list[str] = []
    seen: dict[str, str] = {}
    bad = False
    for g in raw if isinstance(raw, list) else ([] if raw is None else [raw]):
        if (not isinstance(g, dict) or not group_number(g.get("id"))
                or not isinstance(g.get("nodes"), list)):
            bad = True
            continue
        name = g.get("name") if isinstance(g.get("name"), str) and g.get("name") else (
            GROUP_NAME.format(n=group_number(g["id"])))
        if any(x["id"] == g["id"] for x in groups):
            bad = True
            continue
        ids = [x for x in dict.fromkeys(g["nodes"]) if isinstance(x, str)]
        kept = []
        for cid in ids:
            if cid not in held:
                notes.append(GROUP_GONE.format(name=name, node=cid.removeprefix("render:")))
            elif cid in seen:
                notes.append(GROUP_TWICE.format(name=name, node=cid.removeprefix("render:"),
                                                other=seen[cid]))
            else:
                kept.append(cid)
        if refusal is not None and kept:
            ok, words = refusal(kept)
            notes += [GROUP_REFUSED.format(name=name, why=w) for w in words]
            kept = [cid for cid in kept if cid in ok]
        if not kept:
            notes.append(GROUP_EMPTY.format(name=name))
            continue
        for cid in kept:
            seen[cid] = name
        patch = g.get("patch") if isinstance(g.get("patch"), str) else None
        kept_by = g.get("kept_by_host") if isinstance(g.get("kept_by_host"), list) else None
        groups.append(group_entry({"id": g["id"], "name": name, "patch": patch, "nodes": kept,
                                   "open": g.get("open") is True, "kept_by_host": kept_by}))
    if bad:
        notes.append(GROUP_BAD)
    return groups, notes


def _bank_prefix(pid: str) -> str:
    """A bank voice's param prefix, ``lfo.7.depth`` → ``lfo.7.``; "" for
    an id that names no voice (plan 31 B)."""
    head, _, rest = pid.partition(".")
    n, dot, _ = rest.partition(".")
    return f"{head}.{n}." if dot and n.isdigit() else ""


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
        elif key in ("routes", MODIFIERS_KEY, "desk", GROUPS_KEY) and isinstance(v, list):
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
    up at call time, so a hot reload that re-classes it reaches them.

    Plan 44 D3: what is loaded is this object's own — `landing`, (the
    loaded preset's name, what its load or save produced — the signature
    the dirty dot compares against —, how to re-apply it), which
    `Library._landed` / `current` / `is_dirty` hand here for the presets
    group (`Library._owner`) — and so are the preset's bus cuts (`bus`)."""

    # on the class: a `Presets` from before a hot reload has them
    landing: tuple = (None, None, None)
    bus: RigWires = RigWires()

    def __init__(self, lib, reg, router):
        self.lib, self.reg, self.router = lib, reg, router
        self.note = ""
        self.notes: list[str] = []       # step 1's notes from the last load
        self.migrated = ""               # plan 36 T3: "/N migrated to /9" when that load was old
        self.desk_notes: list[str] = []  # the desk rows the last load dropped (set_desk)
        # plan 28 N2: the GRAPH page's positions of the look's nodes
        self.layout: dict[str, list[float]] = {}
        # 2026-11-02 (G0, row 563): the highest group number this preset has
        # allotted since its load — the file's highest at the load, counting
        # entries the load dropped — so a group's id is never one a group
        # of this preset's life had: the one authority for the next number
        # (`graphview.Edit.land_group` takes `group_high + 1` and bumps it;
        # the `groups` setter raises it to the highest assigned; the marks
        # carry it beside the groups; not saved: a reload starts again from
        # the file's own)
        self.group_high = 0
        # plan 40 T2: the GRAPH page's groups (`GROUPS_KEY` entries; the
        # `groups` property, so an assignment seeds the floor)
        self.groups = []
        # R17 (final review): the live preset came from `new` and has never
        # been saved — save names it (whatever a file of its name holds);
        # a load or a save clears it (`_landed`)
        self.unsaved = False
        # plan 26 A4: the loaded preset's graph section (its instances'
        # params, the renderer's wiring once one is attached)
        self.graph = GraphSection(reg, lib=lib)
        # plan 44 D3: the bus cuts the loaded preset holds (`graph.RigWires`)
        self.bus = RigWires()
        self.landing = (None, None, None)
        # row 563: membership is settled where what the preset holds changes
        # — a landing, the table's modifiers, a bank's voices
        self.graph.on_land = self.settle_groups
        router.table.on_modifiers = self.settle_groups
        for bank in self.banks().values():
            bank.on_change = self.settle_groups
        lib.kind(GROUP, SCHEMA.rpartition("/")[0],
                 load=lambda doc, path: self.load_doc(doc, path),
                 document=lambda name: self.document(name),
                 signature=lambda: self.signature(),
                 versions=VERSIONS,
                 text=lambda doc: dumps(doc))
        lib.on_load(GROUP, lambda name: self._landed(name))
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
        """The loaded preset's name (plan 44 D3: this object's own)."""
        return self.landing[0]

    @property
    def loaded(self):
        """What the last load or save produced — the signature the dirty
        dot compares against; None: nothing to compare (nothing loaded)."""
        return self.landing[1]

    def is_dirty(self) -> bool:
        """Has the live look moved off what the loaded preset produced?
        Within undo's tolerance (`undo.alike`); nothing loaded is clean, a
        new preset never saved (`land_unsaved`'s ()) is dirty."""
        ref = self.loaded
        return ref is not None and not undo.alike(self.signature(), ref)

    @property
    def rig(self) -> RigWires:
        """The bus cuts, as `graph.rig_of` and the hold read a renderer's
        `rig_source` (plan 44 D3: the presets are it)."""
        return self.bus

    def load(self, name: str) -> list[str]:
        """Load a preset by name through the library (which records it as
        the strip's current and its clean reference); returns the ids the
        file names that nothing has."""
        missing = self.lib.load(GROUP, name)
        self._warn(name)
        return missing

    def save_as(self, name: str) -> Path:
        """The live state as a preset (a file of that name is written over,
        its old text kept in the trash)."""
        return self.lib.save_as(GROUP, name)

    def new(self, at: tuple[float, float] = (0.0, 0.0)) -> list[str]:
        """A new preset (plan 35 T7, row 387): the library's fresh values
        for every performance group (the reset `Project.new` uses, so
        nothing of the preset loaded before survives), no routes, the desk
        written out as the default preset layer (a file with no `desk` key
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
                  and not is_resize_id(k) and not is_lookback_id(k)
                  and not is_matte_id(k) and not is_cut_id(k)
                  and not is_segment_id(k)}
        doc = {"schema": SAVE_SCHEMA, "name": UNTITLED_PRESET, "values": values,
               "routes": [], "macros": {},
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
        # 0. the look-back's per-frame ids, read as 60 Hz frames (plan 14
        #    WP6) — a file the launch's migration has not rewritten
        doc, converted = echo_seconds(doc)
        if converted:
            notes.append(f"look-back read in seconds ({converted[0]}"
                         + (f", +{len(converted) - 1}" if len(converted) > 1 else "")
                         + "); save to keep it")
        # 0. and its camera.pan in world units (plan 26 A2): a file from
        #    before stored px. Silent — the shape lands where it was
        doc, _ = pan_world(doc)
        # 0. and its palette as a slice of the HSV cylinder (plan 30 N8): a
        #    file from before stored the fold's centre/width and sat/val
        #    lo/hi. Silent, as the pan is, but for a fold wider than the
        #    slice reproduces
        doc, palette_notes = palette_slice(doc)
        notes += palette_notes
        # 0. and its depths onto the effects' speed and amount params along
        #    their tapers (wave 0 T1): a file from before measured them along
        #    the linear range. Silent, as the pan is — each row's real-unit
        #    reach is kept about its base (`params.retaper_depths`); a save
        #    writes the marker (`UNITS`), and tools/retaper_routes.py
        #    rewrites a library once. Measured against this rig's own effect
        #    files (`self.fx`), the registry's when there is no state
        doc, _ = retaper_depths(doc, self._effect_files())
        # 0. and its render graph (plan 26 A4): read, not yet landed. Plan
        #    36 T3 (W3): a `/7` is read as it is — no section is the empty
        #    frame, black, said; nothing is filled in. An older file is
        #    first rewritten as its `/7` by the one-way migration
        #    (`graphmigrate.seven`, said): the free graph (plan 33 M), the
        #    wired frame in the new ids (plan 35), every hidden edge and D1
        #    placement as its wire, the values of an effect the section does
        #    not name dropped — a desk template's rows counted as the desk
        #    they expand to — and a save writes that `/7` as `/9` (row 394, plan 43 C2)
        #    0. and the one orbit camera (plan 43 C2): a file before `/9`
        #    never named the eye — it drew through the open show's — so it
        #    takes the eye an old show's session held (`Project.old_eye`)
        #    and the camera node's GRAPH position that show kept
        #    (`camera_at`), silent; and the look made whole (plan 44 D3): a
        #    file before `/10` takes what an old show's session and `rig`
        #    held (`Project.old_look`, `old_cuts`), its module labels and
        #    its desk template's name dropped — the template said.
        #    Plan 50: these steps are the one ladder, `graphmigrate.forward`
        #    (a fragment's is `patches.forward`). What the show handed on
        #    for a node this preset's graph does not declare — another
        #    preset's `ghost.2.*` — is the show's leftover, dropped quietly
        #    below, never an "unknown id" (review of #351); the migrated
        #    line is said on the strip (`_warn`), not one of `notes`
        gs = self._graph_section()
        show = getattr(lib, "project", None)
        fwd = graphmigrate.forward(doc, gs.specs(), eye=getattr(show, "old_eye", None),
                                   camera_at=getattr(show, "camera_at", None),
                                   look=getattr(show, "old_look", None),
                                   cuts=getattr(show, "old_cuts", None))
        doc, migrated, from_show = fwd.doc, fwd.migrated, set(fwd.from_show)
        migrate_notes = list(fwd.migrate_notes)
        notes += fwd.notes
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
        for scheme, bank in self.banks().items():
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
                  or is_lookback_id(pid) or is_matte_id(pid) or is_cut_id(pid)
                  or is_segment_id(pid)
                  or graphmigrate.effect_of(pid) is not None):
                # (plan 33 S: a switch's `select` too — its graph declares it;
                # plan 34 Z: and a resize's values (plan 39 T2: a matte's, T3: a
                # cut's); plan 36 T3: and every
                # effect's — instance 1 exists only where its graph names it)
                later[pid] = v
            elif p is None:
                if pid not in from_show:
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
        # plan 43 C2 (row 573): the pose is all six angles or none — a part
        # of one, or a value that is no finite number, is said and the turn
        # left spinning, as a file with no pose leaves it
        turn = read_pose(doc.get(POSE_KEY))
        if doc.get(POSE_KEY) is not None and turn is None:
            notes.append(POSE_UNREAD)
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
        # no `desk` key: a fresh preset's, the default preset layer; an
        # explicit [] is an empty one (every preset control dark, D8)
        if "desk" in doc:
            desk = [Binding.from_json(row) for row in doc.get("desk") or []]
        else:
            desk = fresh_desk(table.profile)
        # plan 28 N1: the modifiers, read before the routes land — each
        # parsed now, so a route onto a ``mod:<n>`` lane no modifier
        # publishes is dropped with a note, like a route onto a param no
        # performer may drive
        mod_docs = []
        for d in doc.get(MODIFIERS_KEY) or ():
            if isinstance(d, dict) and isinstance(d.get("id"), str):
                mod_docs.append(d)
            else:
                notes.append("dropped a modifier entry in the preset: not an object with an id")
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
        # the file parsed, nothing landed yet: one undo step for the whole
        # load, by whichever road it came (undo.py, plan 15 WP1) — with
        # what is loaded now, so undoing it puts the earlier name back too
        undo.push(f"load {doc.get('name') or (path.stem if path else 'preset')}", load=True)
        # 1½. the graph lands first (plan 26 A4): its instances' params
        #     exist before their values do; the ids read for it are sorted now
        held_graph, held_values = gs.mark(), reg.snapshot(part="performance")
        # (membership and every bank voice's values, before anything moves)
        held_mods = table.modifiers_doc(reg)
        held_banks = {s: b.doc() for s, b in self.banks().items()}
        # (row 563: the landing settles the groups still loaded — a refusal
        # puts them back, and the floor under their numbers)
        held_groups, held_high = copy.deepcopy(self.groups), self.group_high
        # from here to the values landing, anything that raises puts the
        # graph that was there back, with its instances' values: a load is
        # refused whole, never half a graph
        try:
            gs.land(spec, section)
            # R19 (row 354: "rebuilds, not loads"): a load's delays start
            # empty — no trail of the preset before in this one
            # (plan 38 B3: while held, the preview's — the projector's at Take)
            reset = getattr(getattr(gs, "hold", None) or gs.renderer, "reset_delays", None)
            if callable(reset):
                reset()
            # the modifiers and their params (plan 28 N1), landed with the
            # values: their entries are their params' values
            notes += table.set_modifiers(mods, reg)
            values.update(reg.snapshot(group=modifiers.GROUP))
            for scheme, ids in members.items():          # plan 31 B: the banks
                self.banks()[scheme].set(ids)
            late: list[str] = []
            for pid, v in later.items():
                p = reg.get(pid)
                if p is None:
                    if pid not in from_show:
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
            # 2. every performance param: the file's value, else the value its
            #    object was built with (plan 44 D3: `_fresh_of`, never a
            #    group's `default.json`; a session key of a performance
            #    group, `ghost.mirror`, is never touched)
            by_group: dict[str, dict[str, Any]] = {g: {} for g in PERFORMANCE_GROUPS}
            for pid, v in values.items():
                by_group[reg[pid].group][pid] = v
            landed: dict[str, Any] = {}
            for group in PERFORMANCE_GROUPS:
                fresh = {k: v for k, v in lib._fresh_of(group).items()
                         if k in reg and part_of(reg[k]) == "performance"}
                landed.update({**fresh, **by_group[group]})
            # a value that will not take (a hand-edited "fast" on a number)
            # must not leave half the look on this preset and half on the
            # last: the state as it was goes back and the load is refused whole
            before = reg.snapshot(part="performance")
            try:
                lib.restore(landed)
            except (ValueError, TypeError) as e:
                lib.restore(before)
                raise ValueError(f"a value would not land ({e}); nothing loaded") from e
            # 2. and the turn (plan 43 C2): set to the file's pose. The one
            #    view is what both renderers draw (hold.ONE_FOR_BOTH), so
            #    while the projector is held the pose waits on the hold and
            #    lands at Take (Drop forgets it: review 2.3) — the held
            #    projector never jumps to another turn mid-set
            view = getattr(reg, "view", None)
            hold = getattr(gs, "hold", None)
            if callable(getattr(hold, "hold_pose", None)):
                hold.hold_pose(turn)          # (None: a load with no pose clears it)
            elif turn is not None and callable(getattr(view, "set_pose", None)):
                view.set_pose(turn)
        except BaseException:
            if table.modifiers_doc(reg) != held_mods:     # the modifiers as they were
                table.set_modifiers(held_mods, reg)
            for scheme, ids in held_banks.items():        # the banks as they were
                bank = self.banks()[scheme]
                if bank.doc() != ids:
                    bank.set(ids)
            if gs.mark() != held_graph:          # the graph as it was
                gs.put(held_graph)
            # then every value as it was — the graph instances', and a bank
            # voice's that the load removed and the line above re-added
            # fresh (`held_values` was taken before `bank.set`): a refused
            # load leaves LFO 5's depth where it stood, not at its default
            lib.restore({k: v for k, v in held_values.items() if k in reg})
            self.groups, self.group_high = held_groups, held_high
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
        # 6. each performance group's strip clean against what landed, naming
        #    no module preset (plan 44 D3: the labels are retired, row 540)
        for group in PERFORMANCE_GROUPS:
            if group in NO_MODULE and group not in RETIRED_MODULES:
                continue
            lib.label(group, None)
        # 6¼. the bus cuts (plan 44 D3): the file's, else every cable standing
        self.bus = RigWires.read(doc.get(BUS_KEY))
        # 6½. where the GRAPH page's nodes sit (plan 28 N2): none is the
        #     automatic layout; an entry that is not a name and two numbers
        #     is dropped with a note; an old canvas id is read in today's
        #     (R14), and a save writes today's (row 394)
        positions, bad = read_positions(doc.get(LAYOUT_KEY))
        self.layout = graphmigrate.renamed_layout(positions)
        if bad:
            notes.append(f"layout: {bad} entr{'y' if bad == 1 else 'ies'} unreadable, ignored")
        #     plan 40 T2 (D4): and its groups — a member the graph does not
        #     hold left out, said, a group left empty dropped; no key is no
        #     group (`graphmigrate.groups_of`)
        raw_groups = graphmigrate.groups_of(doc)
        self.groups, group_notes = read_groups(raw_groups, self._held_canvas(), self._groupable)
        notes += group_notes
        #     and the floor under the next group's number: every id the file
        #     named, kept or dropped (row 563: an id is never handed out twice)
        self.group_high = max((group_number(g.get("id")) for g in raw_groups
                               if isinstance(g, dict)), default=0)
        # 7. the notes, for the panel
        self.notes = notes
        self.migrated = migrated            # plan 36 T3: the one-way migration's word
        self._warn(str(doc.get("name") or (path.stem if path else "preset")))
        return unknown

    def document(self, name: str) -> dict:
        """The live state as a preset document, named — what a save writes."""
        # row 394 (the owner, 2026-10-25): every save is the newest schema,
        # in today's words — both Macs run the same build, so nothing is
        # written down for an older one (D1's lowest-schema rule, R10 and
        # R15 are superseded); plan 44 D3: `/10`, groups or none
        doc: dict[str, Any] = {"schema": SAVE_SCHEMA, "name": name}
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
        for bank in self.banks().values():
            if bank.doc() != list(bank.DEFAULT):
                doc[bank.KEY] = bank.doc()
        values = self._values()
        # plan 36 T3 (W3): an effect exists only where the section names it
        # — the values of one it does not (a rig's, before any graph
        # landed) are not the preset's
        held = graphmigrate.section_effects(doc[GRAPH_KEY])
        values = {k: v for k, v in values.items()
                  if graphmigrate.effect_of(k) in (None, *held)}
        # plan 43 C2 (row 573): the spin's pose, after the bases — every save
        # (the migration's resave takes it back out of a file that had none:
        # `headless.resave`)
        pose = self._pose()
        doc.update(values=values, **({POSE_KEY: pose} if pose else {}),
                   routes=[b.to_json() for b in table.routes()],
                   **self._modifiers_part(name),
                   **self._desk_part(name), macros=table.macros_doc(),
                   **{UNITS_KEY: dict(UNITS)})
        # plan 44 D3: the bus cuts, when any cable is cut
        bus = self.bus.to_json()
        if bus:
            doc[BUS_KEY] = bus
        layout = getattr(self, "layout", None)
        if layout:                      # plan 28 N2: a preset with none writes none
            doc[LAYOUT_KEY] = {k: list(layout[k]) for k in sorted(layout)}
        # plan 40 T2 (D4, D7): the groups, after the layout, each of what the
        # preset still holds; a preset with none writes none (the schema is
        # `/9` either way: plan 43 C2, row 576)
        groups = self.live_groups()
        if groups:
            doc[GROUPS_KEY] = groups
        # plan 32 S: the channels' bins
        media = self.media
        if media is not None:
            doc[MEDIA_KEY] = media.to_json()
        return doc

    def banks(self) -> dict:
        """The router's modulator banks by scheme (plan 31 B); none on a
        router that steps none (the tests' bare ones). Public (plan 40
        review fix): GRAPH's spawn reads them for its `patches.Host`."""
        banks = getattr(self.router, "_banks", None)
        return banks() if callable(banks) else {}

    def _pose(self) -> dict[str, float]:
        """The spin's pose, the `pose` section (plan 43 C2): the view's six
        angles, its body folded in (`ViewState.pose`), by `POSE_IDS` — none
        on a registry with no view (a test's, one from before C2). While the
        projector is held with a loaded pose waiting (review 2.3), that pose:
        it is the loaded preset's turn, not the program's."""
        view = getattr(self.reg, "view", None)
        if not callable(getattr(view, "pose", None)):
            return {}
        waiting = getattr(getattr(self._graph_section(), "hold", None), "pose", None)
        if waiting is not None:
            return {pid: pose_angle(a) for pid, a in zip(POSE_IDS, waiting, strict=True)}
        return {pid: pose_angle(a) for pid, a in zip(POSE_IDS, view.pose(), strict=True)}

    def _values(self) -> dict[str, Any]:
        """The preset's `values`: every performance base but the modifiers'
        params, which their entries hold (so a file saved here loads on an
        older build with no unknown id)."""
        # (plan 38 B3: nor a held program's own nodes, kept while held)
        hold = getattr(self._graph_section(), "hold", None)
        only = hold.program_only() if hold is not None else frozenset()
        return {k: v for k, v in self.reg.snapshot(part="performance").items()
                if not k.startswith(modifiers.PREFIX) and k not in only}

    def _modifiers_part(self, name: str | None = None) -> dict:
        """What a save writes for the modifiers: ``{"modifiers": entries}``
        after the routes, or nothing when there are none."""
        own = self.router.table.modifiers_doc(self.reg)
        return {MODIFIERS_KEY: own} if own else {}

    def _effect_files(self) -> dict:
        """The effect files a document's depths are measured against (wave
        0 T1, `params.retaper_depths`): this rig's own `FxState`'s (the
        graph section's, `GraphSection.fx`), else the registry's, else the
        shader folder's once."""
        state = self._graph_section().fx
        return fx_files(state if state is not None else self.reg)

    def _graph_section(self) -> GraphSection:
        """The graph section's lander; made here for a `Presets` from
        before plan 26 A4 (a hot reload re-classes, never re-inits)."""
        gs = self.__dict__.get("graph")
        if gs is None:
            gs = self.graph = GraphSection(self.reg, lib=self.lib)
            gs.on_land = self.settle_groups
        return gs

    def parts(self) -> tuple:
        """Plan 40 T3: the loaded preset's parts, as `patches.lift` reads them
        (*save as patch*): the landed section (`GraphSpec`, None with none),
        the table (`routing.Bindings`: its routes, preset-layer desk,
        modifiers, macros), the registry's snapshot of the performance
        params (a modifier's params among them; a held program's own nodes
        not, as `_values`) and the GRAPH page's layout. Reads only."""
        hold = getattr(self._graph_section(), "hold", None)
        only = hold.program_only() if hold is not None else frozenset()
        values = {k: v for k, v in self.reg.snapshot(part="performance").items()
                  if k not in only}
        return (getattr(self._graph_section(), "spec", None), self.router.table, values,
                dict(getattr(self, "layout", None) or {}))

    def _held_canvas(self) -> set[str]:
        """Plan 40 T2: the GRAPH canvas ids the loaded preset holds that a
        group may name — its section's render nodes (``render:acid.2``), its
        modifiers, its LFOs and envelopes (the bank's ids; with no bank —
        a test's bare router — the voices the registry holds, the canvas's
        own rule, `graphview.bank_ids`: never an id nothing holds) and the
        eight macros."""
        spec = getattr(self._graph_section(), "spec", None)
        held = {f"render:{n}" for n in patches.spec_names(spec)}
        held |= {m.id for m in getattr(self.router.table, "modifiers", ())}
        banks = self.banks()
        for scheme in ("lfo", "env"):
            bank = banks.get(scheme)
            ids = bank.doc() if bank is not None else graphview.bank_ids(None, self.reg, scheme)
            held |= {f"{scheme}.{n}" for n in ids}
        held |= {f"macro.{n}" for n in range(1, patches.MACROS + 1)}
        return held

    def _groupable(self, ids: list[str]) -> tuple[set[str], list[str]]:
        """Plan 40 T2: of canvas ids `ids`, those a group may hold and the
        words for the rest (`patches.groupable`, plan 50: any node the preset saves)."""
        members, refused = patches.groupable(getattr(self._graph_section(), "spec", None),
                                          self.router.table, ids)
        return set(members.canvas()), refused

    @property
    def groups(self) -> list[dict]:
        """The GRAPH page's groups (plan 40 T2), the live list. Assigning
        raises `group_high` to the highest number assigned (row 563), so a
        number is never handed out twice however the list arrived — a
        load, a mark put back, a test's own entries."""
        d = self.__dict__
        if "_groups" not in d:                  # (an instance from before the property)
            d["_groups"] = d.pop("groups", [])
        return d["_groups"]

    @groups.setter
    def groups(self, value) -> None:
        groups = list(value or ())
        self.__dict__["_groups"] = groups
        top = max((group_number(g.get("id")) for g in groups if isinstance(g, dict)), default=0)
        self.group_high = max(self.__dict__.get("group_high", 0), top)

    def settle_groups(self) -> None:
        """2026-11-02 (G0, row 563): membership updated at once. Every
        member the preset no longer holds (`_held_canvas`: a render node
        the section just landed without, a modifier or a voice just removed)
        is taken out of its group's list, in place, and a group left with
        none is taken out of the list — in the same operation that removed
        the node, so the next draw and the next save find the lists already
        right. Hung on the mechanisms, not the callers: the graph section's
        `on_land`, the table's `on_modifiers`, each bank's `on_change`."""
        groups = self.groups
        if not groups:
            return
        held = self._held_canvas()
        for g in list(groups):
            nodes = g.get("nodes") or []
            left = [cid for cid in nodes if cid in held]
            if len(left) == len(nodes):
                continue
            if left:
                g["nodes"] = left
            else:
                groups.remove(g)

    def live_groups(self) -> list[dict]:
        """Plan 40 T2: the groups as a save writes them — each member the
        preset no longer holds left out, a group left with none left out —
        in the file's key order. Since row 563 the lists are kept so as the
        nodes go (`settle_groups`); this stays the save's own guard."""
        groups = getattr(self, "groups", None) or []
        if not groups:
            return []
        held = self._held_canvas()
        out = []
        for g in groups:
            nodes = [cid for cid in g.get("nodes", ()) if cid in held]
            if nodes:
                out.append(group_entry({**g, "nodes": nodes}))
        return out

    def _desk_part(self, name: str | None = None) -> dict:
        """What a save writes for the desk: ``{"desk": rows}``, the whole
        preset layer (plan 44 D3: the desk templates are retired)."""
        return {"desk": desk_json(self.router.table.desk())}

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
                {s: b.doc() for s, b in self.banks().items()},
                # plan 28 N2: a node moved on the GRAPH page; none, no part
                json.dumps(getattr(self, "layout", None) or None, sort_keys=True),
                # plan 32: a bin entry assigned or cleared
                None if self.media is None else json.dumps(self.media.to_json()),
                # plan 40 T2: a group made, opened, renamed or taken apart
                json.dumps(getattr(self, "groups", None) or None, sort_keys=True),
                # plan 44 D3: a bus cable cut or joined on GRAPH
                json.dumps(self.bus.to_json(), sort_keys=True))

    # ---- internals ----

    def _warn(self, name: str) -> None:
        """The strip's warning line: the load's first note — else (plan 36
        T3) that an old file was migrated to the newest schema on load,
        until it is saved."""
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
