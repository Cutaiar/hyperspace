"""The preset — one file that holds everything a performance moment is
(plan 13 D1, §2.1): ``hyperspace.preset/2``.

  {"schema": "hyperspace.preset/2", "name": "TRIP", "note": "…",
   "values": {id: base, …},            the performance part (params.PARTS)
   "routes": [row, …],                 the performer rows (routing.Binding)
   "desk":   [row, …],                 the APC40's preset layer (routing.Binding)
   "macros": {"macro.1": {…}, …},      the macros' labels and subscribers
   "modules": {"fx": "trip", …}}       module-preset labels (D3)

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
   ``routes`` row that is not a performer row, a second performer on one
   target (the referee's, below);
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
   (`Bindings.set_macros`) and land the base subscribers at once from the
   macros' bases just landed (`Router.follow_macros(force=True)`). The
   macro is the scene-setter of record: a param a base subscriber names
   ends at the subscriber's value even when ``values`` names it too;
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

The factory presets are generated (`python -m hyperspace.preset`,
`write_factory`, pinned by tests/test_presets.py): the code below holds
the generator's inputs — plan 12's five party presets' routes and their
desk blocks, and whole the five that were routing presets (``legacy6``,
``lfo-breathe``, ``hands-fx``, ``hands-pinch``, ``hands-play``,
`FACTORY_PRESETS`); every factory preset's ``desk`` is the factory
preset layer unless its entry says otherwise. The house presets' and the
party presets' values are data in their files.

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

from . import apc40, routing
from .bands import BANDS
from .lfo import SHAPES, SYNCS
from .library import (
    DEFAULT_PROJECT,
    FACTORY,
    PERFORMANCE_SCHEMA,
    PRESETS,
    PROJECT_SCHEMA,
    PROJECT_SUFFIX,
    PROJECT_V1,
    PROJECTS,
    SLOTS,
    LibraryError,
    _write_text,
    slug,
)
from .params import PERFORMANCE_GROUPS, PLANES, SESSION_GROUPS, part_of
from .routing import LANE_SCHEMES, MOD_OPS, Binding, Macro, Sub

SCHEMA = PERFORMANCE_SCHEMA
GROUP = PRESETS                   # the library folder, and the strip's group
FACTORY_DIR = FACTORY / GROUP


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
    — what a file with no ``desk`` key gets, and every factory preset's."""
    return [b for b in routing.factory_desk(profile) if b.layer == "preset"]


def dumps(doc: dict) -> str:
    """A preset as file text: one route or desk row per line, so a diff
    reads as a binding; the values one per line."""
    parts = []
    for key, v in doc.items():
        if key in ("routes", "desk") and isinstance(v, list):
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
        self.desk_notes: list[str] = []  # the desk rows the last load dropped (set_desk)
        lib.kind(GROUP, SCHEMA.rpartition("/")[0],
                 load=lambda doc, path: self.load_doc(doc, path),
                 document=lambda name: self.document(name),
                 signature=lambda: self.signature(),
                 versions=(int(SCHEMA.rpartition("/")[2]),),
                 text=lambda doc: dumps(doc))
        lib.on_load(GROUP, lambda name: self._landed(name))
        lib.presets = self

    # ---- the API ----

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

    def load_doc(self, doc: dict, path: Path | None = None) -> list[str]:
        """Apply a preset document — the kind's loader (plan 13 §5).
        Returns the unknown ids; the notes land in `notes`."""
        lib, reg, table = self.lib, self.reg, self.router.table
        notes: list[str] = []
        # 1. what the file names that a preset may not carry — all parsed
        #    before anything lands, so a bad row leaves the state alone
        values: dict[str, Any] = {}
        unknown: list[str] = []
        for pid, v in dict(doc.get("values") or {}).items():
            p = reg.get(pid)
            if p is None:
                unknown.append(pid)
            elif part_of(p) == "session":
                notes.append(f"{pid} is the session's, ignored")
            elif part_of(p) is None or not p.persist:
                notes.append(f"{pid} is not part of a preset, ignored")
            else:
                values[pid] = v
        if unknown:
            shown = ", ".join(unknown[:4]) + ("…" if len(unknown) > 4 else "")
            notes.append(f"{len(unknown)} unknown id(s): {shown}")
        routes: list[Binding] = []
        for row in doc.get("routes") or []:
            b = Binding.from_json(row)
            if b.scheme not in LANE_SCHEMES or b.op not in MOD_OPS:
                notes.append(f"dropped {b.source} → {b.target} ({b.op}): not a performer row")
                continue
            routes.append(b)
        # no `desk` key: a fresh preset's, the factory preset layer; an
        # explicit [] is an empty one (every preset control dark, D8)
        if "desk" in doc:
            desk = [Binding.from_json(row) for row in doc.get("desk") or []]
        else:
            desk = fresh_desk(table.profile)
        # a bad subscriber raises before anything lands; a route's scale is
        # settled as the table's are (decision register row 18 (a)): on a
        # macro a depth subscriber, on a performance param dropped, noted
        held = routing.macros_of(doc.get("macros"))
        notes += routing.migrate_scales(routes, held)
        macros = {mid: m.to_json() for mid, m in held.items()}
        modules = dict(doc.get("modules") or {})
        for group in list(modules):
            if group not in PERFORMANCE_GROUPS or group == "macro":
                notes.append(f"module {group}: not a performance group, ignored")
                modules.pop(group)
        # 2. every performance param: the file's value, else its group default
        by_group: dict[str, dict[str, Any]] = {g: {} for g in PERFORMANCE_GROUPS}
        for pid, v in values.items():
            by_group[reg[pid].group][pid] = v
        landed: dict[str, Any] = {}
        for group in PERFORMANCE_GROUPS:
            landed.update(lib.resolved(group, by_group[group]))
        # a value that will not take (a hand-edited "fast" on a number) must
        # not leave half the look on this preset and half on the last: the
        # state as it was goes back and the load is refused whole
        before = reg.snapshot(part="performance")
        try:
            lib.restore(landed)
        except (ValueError, TypeError) as e:
            lib.restore(before)
            raise ValueError(f"a value would not land ({e}); nothing loaded") from e
        # 3. every performer row replaced; the referee keeps the first
        table.set_routes(routes)
        notes += [f"dropped {b.source} → {b.target}: {why}" for b, why in table.dropped]
        # 4. the desk's preset layer replaced; the layer drops to it (D4)
        #    and the MIDI adapter redraws, the faders' catch cleared
        self.desk_notes = table.set_desk(desk)
        notes += self.desk_notes
        # 5. the macros replaced, their base subscribers landed now from the
        #    macro bases step 2 put down — the macro is the scene-setter of
        #    record, so its subscriber's value stands over `values`
        table.set_macros(macros)
        self.router.follow_macros(force=True)
        self.note = str(doc.get("note") or "")
        # 6. the module labels: a label and a clean dot, never a load (D3)
        for group in PERFORMANCE_GROUPS:
            if group == "macro":
                continue
            label = modules.get(group)
            lib.label(group, str(label) if label else None)
        # 7. the notes, for the panel
        self.notes = notes
        self._warn(str(doc.get("name") or (path.stem if path else "preset")))
        return unknown

    def document(self, name: str) -> dict:
        """The live state as a preset document, named — what a save writes."""
        lib = self.lib
        modules = {g: lib.current(g) for g in PERFORMANCE_GROUPS
                   if g != "macro" and lib.current(g)}
        doc: dict[str, Any] = {"schema": SCHEMA, "name": name}
        if self.note:
            doc["note"] = self.note
        table = self.router.table
        doc.update(values=self.reg.snapshot(part="performance"),
                   routes=[b.to_json() for b in table.routes()],
                   desk=desk_json(table.desk()), macros=table.macros_doc(),
                   modules=modules)
        return doc

    def signature(self) -> tuple:
        """What the strip's dirty dot compares: the performance bases, the
        performer rows, the desk's preset layer and the macros, each as it
        would be written."""
        table = self.router.table
        return (self.reg.snapshot(part="performance"),
                json.dumps([b.to_json() for b in table.routes()]),
                json.dumps(desk_json(table.desk()), sort_keys=True),
                json.dumps(table.macros_doc(), sort_keys=True))

    # ---- internals ----

    def _warn(self, name: str) -> None:
        if self.notes:
            more = f" (+{len(self.notes) - 1} more)" if len(self.notes) > 1 else ""
            self.lib.warning = f"preset {name}: {self.notes[0]}{more}"

    def _landed(self, name: str | None) -> None:
        """The library's load hook: the bank lights the slot that names
        what just loaded, whichever road it came in by (the strip, an F-key,
        a file edited on disk); a preset the bank does not name lights none."""
        pr = self.lib.project
        pr.active = pr.bank.index(name) if name in pr.bank else -1


# ---------------------------------------------------------------- factory inputs

# ---- plan 12: the party presets — one per render attraction, two hands ----
#
# Lane numbers assume the default six dofs per hand (hands/core.py
# DEFAULT_DOFS: x, y, z, roll, pitch, yaw; left 0–5, right 6–11), which
# tests/test_plan12_presets.py pins to the hands package. Every hand row
# is a `push` from the axis's own rest — a level or absent hand adds
# nothing, so the scene's bases come back when the hand leaves the box
# with or without the audit's B1 fix — except the three `position` rows
# on wrap / centred params whose base *is* the axis's rest value
# (dream.hue 0, fx.kaleido.swirl 0, lfo.1.depth 0): same rule, same
# result. docs/plans/12-presets.md is the design; the performer cards
# are docs/plans/assets/12-presets/<name>.md.
HAND_AXES = ("x", "y", "z", "roll", "pitch", "yaw")
TURN = 0.25      # a phase push's depth: ±45° across a tilt's throw


def hand(side: str, axis: str) -> str:
    """`hand:<i>` for "L"/"R" and an axis name, on the default dofs."""
    return f"hand:{('L', 'R').index(side) * len(HAND_AXES) + HAND_AXES.index(axis)}"


def _push(side: str, axis: str, target: str, depth: float, **kw) -> Binding:
    return Binding(hand(side, axis), target, "push", depth, **kw)


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
    pattern input 2 — the hex cells' scale, the one spatial input the
    scene's pattern reads, which lane 2 then leaves alone — and fingers
    up tip the camera to look down onto the faces."""
    return [*_lane_rows(skip_mods=(2,)), *_grip_rows(),
            _push("L", "y", "view.bright", 0.14),
            _push("R", "y", "view.pattern_mix", 0.6),
            _push("R", "z", "camera.zoom", -0.3),
            _push("R", "roll", "pattern.mod.2", 0.7),
            _push("R", "pitch", "camera.pitch", 0.5)]


def party_field_routes() -> list[Binding]:
    """The instance field. Right height is the crowd: more copies, the
    camera pulling back to keep them in frame and a touch more light so
    the small copies read; right roll and yaw turn every copy at once in
    XW and ZW. Left hand flies the field — sideways and reaching in pan
    it — and left height pushes how far the copies swing."""
    return [*_lane_rows(),
            _push("R", "y", "view.instances", 0.6),
            _push("R", "y", "camera.zoom", -0.15),
            _push("R", "y", "view.bright", 0.1),
            _push("R", "roll", "rot.phase.XW", TURN),
            _push("R", "yaw", "rot.phase.ZW", TURN),
            _push("L", "x", "camera.pan.x", 0.1),
            _push("L", "z", "camera.pan.y", 0.1),
            _push("L", "y", "view.inst_amp", 0.5)]


def party_wake_routes() -> list[Binding]:
    """The look-back wake. Left hand grips the object — moving it is what
    paints the wake — and left height pushes the spin. Right height pushes
    the echoes in, reaching in lengthens them (decay up), right roll
    positions the dream's hue round the whole circle (level = as painted),
    fingers up push the dream buffer's opacity."""
    return [*_lane_rows(), *_grip_rows(),
            _push("L", "y", "view.speed", 0.4),
            _push("R", "y", "dream.echo_mix", 0.7),
            _push("R", "z", "dream.decay", -0.12),
            Binding(hand("R", "roll"), "dream.hue", "position"),
            _push("R", "pitch", "dream.mix", 0.5)]


def party_trip_routes() -> list[Binding]:
    """The effect stack. Right height fires the zoom burst, reaching in
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
            Binding("lfo:0", "camera.zoom", "push", 0.08),
            _push("L", "x", "fx.zoomblur.cx", 0.8),
            _push("L", "z", "fx.zoomblur.cy", -0.8)]


# ---- the routes-only files, full presets now (plan 13 decision 10) ----

def legacy6_values() -> dict[str, float]:
    """The bases the legacy6 routes assume: a push lands the reference's
    number only from 0 (the parity anchor, tests/test_routing.py)."""
    return {**{f"rot.rate.{n}": 0.0 for n in PLANES},
            **{f"pattern.mod.{i}": 0.0 for i in range(len(BANDS))}}


def lfo_breathe_routes() -> list[Binding]:
    """The chaining demonstration (plan 09 decision 7): LFO 1 pushes
    brightness on the bar; the right hand's height positions LFO 1's depth
    — so raising the hand deepens the swell and nothing else moves; LFO 2
    pushes the fx mix on the quarter, through macro 1 as its attenuator
    (a depth subscriber of macro.1, `lfo_breathe_macros`)."""
    return [Binding("lfo:0", "view.bright", "push", 0.5),
            Binding("hand:7", "lfo.1.depth", "position"),
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
            "lfo.1.shape": SHAPES.index("sine"), "lfo.1.depth": 0.6, "macro.1": 0.0}


def lfo_breathe_desk() -> list[Binding]:
    """The factory preset layer, and the Breathe macro on device knob 1."""
    return [*fresh_desk(), device_knob(1, "macro.1")]


def hands_fx_routes() -> list[Binding]:
    """Plan 08's hand-driven effect: the right hand's height positions the
    fx mix, its roll and yaw bend and twist the Acid shader, the left
    hand's roll pushes Acid's speed and its height the brightness."""
    return [Binding("hand:7", "fx.mix", "position"),
            Binding("hand:10", "fx.acid.twist", "position"),
            Binding("hand:3", "fx.acid.speed", "push", 0.5),
            Binding("hand:1", "view.bright", "push", 0.4),
            Binding("hand:11", "fx.acid.bend", "position")]


def hands_pinch_routes() -> list[Binding]:
    """Plan 08's pinch gates: one hand height, two meanings by finger."""
    return [Binding("hand:7", "view.bright", "position", when="hand:18"),
            Binding("hand:7", "view.speed", "position", when="hand:19"),
            Binding("hand:1", "fx.mix", "position", when="hand:14"),
            Binding("hand:1", "camera.zoom", "position", when="hand:15")]


def hands_play_routes() -> list[Binding]:
    """Plan 08's first hand preset: the two heights and the right roll."""
    return [Binding("hand:7", "view.bright", "position"),
            Binding("hand:1", "view.speed", "position"),
            Binding("hand:10", "view.depth4", "position")]


def effects_on(routes, values: dict[str, Any],
               has: Callable[[str], bool] | None = None) -> dict[str, Any]:
    """`values` with the effects its routes drive switched on (PR #29's
    rule, for a routes-only file made a full preset): a route into
    ``fx.<name>.*`` sets ``fx.on`` and ``fx.<name>.on``, one into
    ``fx.mix`` alone sets ``fx.on``, one into ``dream.*`` sets
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
        elif parts[0] == "dream" and len(parts) >= 2 and parts[1] != "on":
            wants.append("dream.on")
        for pid in wants:
            if pid not in out and (has is None or has(pid)):
                out[pid] = True
    return out


def device_knob(k: int, target: str) -> Binding:
    """Device knob `k` (1–8) on the preset layer: absolute, ring feedback —
    the row the factory map gives a knob (apc40._cc)."""
    return Binding.from_json(apc40._cc(target, apc40.DEVICE_KNOBS[k - 1], layer="preset"))


# plan 12 §6: the eight device knobs WAKE and TRIP put their bases on, on
# top of the factory preset layer (the band strip stays behind SHIFT)
WAKE_KNOBS = ("dream.echo_mix", "dream.decay", "dream.darken", "dream.contrast",
              "dream.occlude", "dream.mix", "dream.sat", "dream.k")
TRIP_KNOBS = ("fx.mix", "fx.plasma.level", "fx.kaleido.segments", "fx.kaleido.zoom",
              "fx.zoomblur.amount", "fx.zoomblur.glow", "fx.huecycle.paint",
              "fx.huecycle.spread")


def knob_desk(targets: tuple[str, ...]) -> Callable[[], list[Binding]]:
    return lambda: [*fresh_desk(), *(device_knob(k + 1, t) for k, t in enumerate(targets))]


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
    desk: Callable[[], list[Binding]] | None = fresh_desk


def _lanes() -> list[Binding]:
    return routing.legacy6_routes()


FACTORY_PRESETS: dict[str, Factory] = {
    # plan 12's five, re-cut: routes from code, values data (WP2's)
    "party-tumble": Factory(party_tumble_routes),
    "party-faces": Factory(party_faces_routes),
    "party-field": Factory(party_field_routes),
    "party-wake": Factory(party_wake_routes, desk=knob_desk(WAKE_KNOBS)),
    "party-trip": Factory(party_trip_routes, desk=knob_desk(TRIP_KNOBS)),
    # the routing presets, full presets now (decision 10)
    "legacy6": Factory(_lanes, legacy6_values, "legacy6",
                       "The reference's band → plane table on bases of 0: the parity "
                       "anchor (the planes stand still until the music drives them).",
                       desk=None),
    "lfo-breathe": Factory(lfo_breathe_routes, lfo_breathe_values, "lfo-breathe",
                           "The macro demo: device knob 1 is Breathe — the picture "
                           "brightens and the spin slows as the LFO's swell of the fx mix "
                           "deepens; the right hand's height deepens LFO 1's pulse.",
                           macros=lfo_breathe_macros, desk=lfo_breathe_desk),
    "hands-fx": Factory(hands_fx_routes, lambda: {"fx.acid.speed": 4.0}, "hands-fx",
                        "Plan 08: both hands play the Acid shader and the fx mix.",
                        desk=None),
    "hands-pinch": Factory(hands_pinch_routes, dict, "hands-pinch",
                           "Plan 08: a pinch picks what a hand's height moves.", desk=None),
    "hands-play": Factory(hands_play_routes, dict, "hands-play",
                          "Plan 08: brightness, speed and 4D depth on the hands.", desk=None),
}
# the five party presets (plan 12), by file slug
PARTY = tuple(s for s in FACTORY_PRESETS if s.startswith("party-"))


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
    return doc


def write_factory(directory: Path = FACTORY_DIR) -> list[Path]:
    """Regenerate what the factory presets take from code
    (`python -m hyperspace.preset`): the presets `FACTORY_PRESETS` gives
    values whole (`generated`); the party presets' routes, desk and
    macros; every other preset's ``desk``, the factory preset layer
    (`fresh_desk`). Every other key in a file — the values, the note, the
    modules — is data and stays as it is."""
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
        desk = fresh_desk if spec is None else spec.desk
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
# A second launch finds nothing to do.

MIGRATED = "MIGRATED"             # the preset a home with no project keeps its routes in
NOT_READ = "NOT-READ.txt"         # left in <home>/bindings/ once its files are converted
LEGACY_ROUTING = "bindings"       # the routing presets' old folder in the home


def factory_carried() -> routing.Carried:
    """What a table with no file of its own carries: the lane rows the
    factory table shipped before plan 13 WP5 (the house presets' routes)."""
    return routing.Carried(routes=[b.to_json() for b in routing.legacy6_routes()],
                           desk=None, macros={}, values={})


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
                and desk(a) == desk(b) and macros(a) == macros(b))
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
        values: dict = {}
        sess: dict = {}
        for pid, v in dict(slot.get("values") or {}).items():
            (sess if _part(pid) == "session" else values)[pid] = v
        if not session and sess:
            session = sess
        for pid, v in carried.values.items():
            if _part(pid) == "performance":
                values.setdefault(pid, v)
        doc: dict[str, Any] = {"schema": SCHEMA,
                               "name": str(slot.get("name") or f"PRESET {k + 1}")}
        if slot.get("note"):
            doc["note"] = str(slot["note"])
        doc.update(values=values, routes=copy.deepcopy(carried.routes))
        if carried.desk:
            doc["desk"] = _desk_rows(carried.desk)
        doc.update(macros=copy.deepcopy(carried.macros), modules=dict(modules))
        name, path = put_preset(root, doc, factory)
        bank.append(name)
        notes.append(f"slot {k + 1} → preset {name!r}"
                     + (f" ({path.name})" if path is not None else " (already there)"))
    return bank, session, notes


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
    its F-key loaded while empty slots were seeded. Returns (notes, whether
    a preset now holds `carried`, whether the file was rewritten); a file
    that is not schema 1 is left alone: ([], False, False)."""
    doc = json.loads(path.read_text())
    if not isinstance(doc, dict) or doc.get("schema") != PROJECT_V1:
        return [], False, False
    keep, labels = _labels(doc.get("modules") or {})
    raw = list(doc.get("bank") or [])[:SLOTS]
    raw += [None] * (SLOTS - len(raw))
    bank, first, notes = slot_presets(root, raw, carried, labels, factory)
    try:
        seeds = list(json.loads((factory / PROJECTS / f"{DEFAULT_PROJECT}{PROJECT_SUFFIX}")
                                .read_text()).get("bank") or [])
    except (OSError, ValueError, AttributeError):
        seeds = []
    filled = [n for n in bank if n]
    bank = [n if n or k >= len(seeds) else seeds[k] for k, n in enumerate(bank)]
    session = dict(doc.get("session") or {})
    for pid, v in dict(doc.get("values") or {}).items():
        if _part(pid) == "session":
            session.setdefault(pid, v)
    for pid, v in first.items():
        session.setdefault(pid, v)
    new: dict[str, Any] = {"schema": PROJECT_SCHEMA,
                           "name": str(doc.get("name") or path.name[: -len(PROJECT_SUFFIX)])}
    if doc.get("note"):
        new["note"] = str(doc["note"])
    new.update(startup=filled[0] if filled else next((n for n in bank if n), None),
               bank=bank, session=session, modules=keep)
    bak = routing.backup(path, "1")
    if bak is None:
        return [*notes, f"{path.name} NOT migrated: no backup could be made"], False, False
    _write_text(path, json.dumps(new, indent=1) + "\n")
    notes.append(f"{path.name} → {PROJECT_SCHEMA} ({len(filled)} presets); "
                 f"the old file kept as {bak.name}")
    return notes, bool(filled), True


def _into_default(root: Path, name: str, factory: Path = FACTORY) -> str:
    """`name` as the user default project's startup and first slot — the
    project made from the factory default if the user has none; an
    existing file is kept first (``.bak-v2``). The rest of the bank moves
    one slot along; a name pushed off the end keeps its file."""
    path = root / PROJECTS / f"{DEFAULT_PROJECT}{PROJECT_SUFFIX}"
    fresh = not path.is_file()
    src = factory / PROJECTS / path.name if fresh else path
    doc = json.loads(src.read_text())
    if not isinstance(doc, dict) or doc.get("schema") != PROJECT_SCHEMA:
        raise ValueError(f"{path.name} is not a {PROJECT_SCHEMA} project")
    bank =[n for n in list(doc.get("bank") or [])[:SLOTS] if n != name]
    bank.insert(0, name)
    bank += [None] * (SLOTS - len(bank))
    gone = ""
    if len(bank) > SLOTS:
        spare = next((k for k in range(len(bank) - 1, 0, -1) if bank[k] is None), None)
        if spare is not None:
            bank.pop(spare)
        else:
            gone = f"; {bank.pop()!r} left the bank (its file stays)"
    doc.update(bank=bank, startup=name)
    if fresh:
        doc["name"] = DEFAULT_PROJECT
        doc.pop("note", None)
        _write_text(path, json.dumps(doc, indent=1) + "\n")
        return f"{path.name}: made from the factory default, {name!r} its startup{gone}"
    bak = routing.backup(path, "2")
    if bak is None:
        raise OSError(f"{path.name}: no backup could be made")
    _write_text(path, json.dumps(doc, indent=1) + "\n")
    return f"{path.name}: {name!r} its startup and slot 1{gone}; the old file kept as {bak.name}"


def migrate_routing_presets(root: Path, has: Callable[[str], bool] | None = None,
                            factory: Path = FACTORY) -> list[str]:
    """Every user routing preset (``<home>/bindings/*.json``) as a full
    preset (decision 10): its values (less session ids, with the effects
    its routes drive switched on, `effects_on`), its performer rows (a
    ``scale: macro.N`` a depth subscriber), its macros, no ``desk`` key.
    The files stay where they are, untouched; a note beside them
    (NOT_READ) says they are no longer read, and is what makes this run
    once."""
    folder = root / LEGACY_ROUTING
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    if not files or (folder / NOT_READ).exists():
        return []
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
        doc = {"schema": SCHEMA, "name": str(raw.get("name") or f.stem),
               "note": f"the routing preset bindings/{f.name}, made a preset (plan 13 WP5)",
               "values": effects_on(routes, values, has), "routes": routes,
               "macros": t.macros_doc(), "modules": {}}
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


def migrate_home(lib, router) -> list[str]:
    """Plan 13 §6's one-time migration of the library home (see above):
    the schema-1 projects, the user routing presets, then `bindings.json`
    — its preset part (`Bindings.carried`) into the presets first (a
    ``MIGRATED`` preset when no project took it), and only then the file
    rewritten with the session's controls. Re-opens the default project
    when one changed. Every note goes to stderr and the sum to
    `lib.warning`; returns the notes. Nothing to do: nothing written."""
    root, table = lib.home, router.table
    reg = lib.reg
    factory = lib.factory
    carried = table.carried
    use = carried if carried is not None else factory_carried()
    notes: list[str] = []
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
    notes += migrate_routing_presets(root, (lambda pid: pid in reg) if reg is not None
                                     else None, factory)
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
            written.append(root / PROJECTS / f"{DEFAULT_PROJECT}{PROJECT_SUFFIX}")
            held = True
        except (OSError, ValueError, LibraryError) as e:
            notes.append(f"bindings.json's routes NOT moved ({e}); the file is left as it is")
    if carried is not None and table.path is not None and (held or carried.empty):
        if table.notes:
            table.announce(table.path)
        # no file yet (an old midi_map.json's rows, carried): nothing to keep
        fresh = not table.path.exists()
        bak = None if fresh else routing.backup(table.path, table.read_at)
        kept = "" if fresh else f"; the old file kept as {bak.name}" if bak else ""
        if bak is None and not fresh:
            notes.append("bindings.json NOT rewritten: no backup could be made")
        else:
            table.write()
            if table.error:
                notes.append(f"bindings.json NOT written ({table.error}){kept}")
            else:
                table.carried = None
                notes.append(f"bindings.json now holds only the session's controls{kept}")
                written.append(table.path)
    if written:
        lib._sync(*written)
    if projects:
        lib._open_default()
        lib.report(lib.project._apply(), lib.project.name)
    for n in notes:
        print(f"migrate: {n}", file=sys.stderr)
    if notes:
        lib.warning = (f"plan 13 migration: {len(written)} file(s) rewritten, backups beside "
                       "them — the details are on stderr")
    return notes


if __name__ == "__main__":
    for p in write_factory():
        print(p, file=sys.stdout)
