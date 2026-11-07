"""Learn — the one armed param, shared by every adapter that can complete it.

Right-click → Learn arms a param id here, with what the learn waits for
(`want`, plan 17 WP2): **Learn desk** arms ``"desk"``, **Learn hand ▸
left / right** arms ``"hand:left"`` / ``"hand:right"``, and nothing else
can complete it (`accepts`). The MIDI adapter completes a desk learn with
the message it received (midi.py, ``MidiIO._learned`` → `learn_control`
→ an ``abs`` / ``rel`` / ``toggle`` MIDI row); the hands adapter a hand
learn with the axis *of that hand* that moved furthest (hands/core.py,
``HandsIO._learn`` → ``learn_source`` → a route: a ``push`` about the
param's base at the meta controller's learn depth wherever the axis or the
target's range is centred, the ``position`` fader only for a one-sided
axis on a one-sided param or a discrete target — plan 18 WP3, `_row`). A
row already in the table is never rewritten: this is what a *new* learn
lands with. A knob
bumped during a hand learn does its own job; a hand waved during a desk
learn does nothing. A bare ``arm(pid)`` (`want` None) takes whichever
comes first, as every learn did before plan 17. Until plan 11 this state
lived in ``MidiIO``, so with ``[midi] enabled = false`` — or the adapter
failing to open — there was no hand Learn at all (audit B3). Now
``app.main`` builds one ``Learn`` over the live table whatever the MIDI
gate says and hands it to both adapters and to the panel.

A learn writes into the **loaded patch** (plan 13 §3.3, D5): the row
goes into the live table — a knob's as a patch-layer desk row, a hand's
as a route — and no file is written. The loadable patch's dirty dot (loadable.py,
`LoadedPatch.signature` over the table) shows it until a save (⇧F, the loadable patch
strip's save / as…); loading the loadable patch again throws it away. A desk learn
on an invariant control or with the global layer up is refused
(`learn_control` calls `refuse`): the reason is `last`, `refused` is set,
nothing changes, and the learn **stays armed** (plan 17 fork 6) — the
next control that can take it does.

**Unbind** is here too (plan 17 WP1): `unbind` removes what is bound to a
param in the loaded patch — its patch-layer desk rows and its routes,
one kind or both — as one undo step, whether or not a MIDI adapter
exists. `bound` is the same question without the edit (the menu asks it
to know what to list and whether to offer the item at all). A meta row
(invariant or global layer) is never removed (D5, D6).

**Learn sink ▸ <role>:<channel>** (plan 27 B3) routes a param *out*: the
menu lists the meta controller's sink ports (`sinks`, the device registry's
`sink_ports`) and a pick lands at once (`learn_sink`) — there is nothing to
wait for — as a sink row, ``param:<id> → <role>:<channel>`` (routing.py,
`SINK_OP`), in the **meta controller** (`bindings.json`, written now: sinks are
meta controller, D1 / D9), like a pad learn: no undo step, no loadable patch dirt. It replaces
whatever that port sent before (one source per sink port) and never asks
Replace / Keep: a sink row is not a performer.

**Click a control, then a param** (plan 17 WP4) is the same road taken
from the other end: `pick` holds a desk control (`control`, the on-screen
desk's click), and `map_picked(pid)` is `arm(pid, "desk")` then
`learn_control(control)` — so the op, the feedback, the refusals (D5, D6),
the undo step and the message are the knob learn's. A pick and an armed
learn never stand together: arming lets the pick go, picking cancels the
learn. Which params the on-screen desk offers a pick first is `ranked`
(plan 24 C3), a pure function over the loadable patch's values, its group
defaults, its routes and macros, and `cannot_show` — the rule the desk
coverage report (tools/desk_coverage.py) calls a control "dead" by.

Two things the object owns:

  * **`learning`** — the armed param id, or None. Arming forgets a held
    question: the new learn is what the performer means now. Adapters key
    off it and clear it *before* the referee answers, so a hand cannot
    complete the same learn twice while the prompt is up.
  * **`pending`** — a learn the referee refused, ``(new row, the target's
    current performer)``, held for the panel's Replace / Keep prompt
    (ui_routing.py) rather than taking the target or being lost. The
    table is untouched until ``resolve_pending`` answers.

``learn_source`` resolves a ``band.sel.*`` alias to the band it stands
for (audit B4): an alias is not modulatable, so a route on it would sit
in the table doing nothing. So that resolution is this object's, not the
table's. A band, though, is the meta controller's, so that learn is then
refused: **no row of a loadable patch may drive a meta param** (register row 743,
`routing.meta_refusal`), and both learns say so. The factory's own desk
rows on them are the meta controller's and stay. The rule itself is
the registry's (``Registry.real``, installed by ``build_registry``), the
same one the panel's widgets read through; a registry without it (a
bare test rig) learns the alias as armed.

**A pair that overlaps a mapping asks** (register row 754): a row a person
makes on a ``pair:`` lane, by any road, while either pole already has a row
waits as a `PairAsk` for **keep both**, **let the pair take over** or
**cancel** (`settle_pair`). A row from a file never comes this way.

Imports nothing from the adapters or the panel: the registry and the
table are all it needs.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from . import lfo, modifiers, undo
from .envelope import GROUP as ENV_SCHEME
from .graph import pin_node, source_into
from .motion import DEFAULT_ROUTE_FEEL
from .params import (
    PATCH_GROUPS,
    Kind,
    Param,
    Registry,
    is_lookback_knob,
    is_per_deck_meta_id,
)
from .routing import (
    HELD_ONLY,
    MOD_OPS,
    PAIR_SCHEME,
    SAVE_PARAM,
    SINK_OP,
    TURN_OP,
    Binding,
    Bindings,
    Owned,
    base_scheme,
    is_meta_row,
    meta_refusal,
    pair_address,
    pair_poles,
    parse_sink,
    qualified,
    row_words,
    whole_circle,
)

# plan 24 C1: the desk's SAVE is held, never latched — a learned toggle or
# button row would leave it on, and every bank pad's tap would then save
# row 755: a desk Learn on a meta param that is one per `Deck` would be a patch's row, so it
# is refused (the owner, seventh round); these say where a person's road is
PER_DECK_ROAD = "use Learn pad, a key, or the APC's factory rows"
SAVE_REFUSAL = ("Save is the desk's SAVE (track 8's clip stop, held) — it takes no "
                "learned control")

# what an armed learn may wait for (`Learn.want`, `Learn.wants`) is the
# device registry's to say (plan 27 B2: each device's `wants` — "desk" for
# every MIDI role, "hand:left" / "hand:right" for the hands, "pad" for the
# gamepad, a new device's role for it), and "desk" always: a click on the
# on-screen desk completes a desk learn with no device at all. A Learn the
# registry has not been handed (a bare test rig, the probe) offers what
# today's meta controller offers
DESK = "desk"
# plan 56: a pair's two wants, its model — "pair" a step row (`Learn.learn_pair`),
# the neutral default; "pair (spring)" a route, as a stick's. Devices restate them
PAIR_WANT, PAIR_SPRING_WANT = "pair", "pair (spring)"
PAIR_WANTS = (PAIR_WANT, PAIR_SPRING_WANT)
BARE_WANTS = (DESK, "hand:left", "hand:right", "pad", *PAIR_WANTS)
PAD_SCHEMES = ("pad", "hat", "axis", "pair", "touch", "motion")  # what can complete a "pad" learn

# a push learn's depth when the adapter names none (plan 18 WP3). The hands
# adapter passes its own `hands.learn_depth`, whose default is this number
# written a second time: hands/core.py imports nothing from the package
# (tests/test_learn.py::test_the_two_default_depths_agree holds them equal)
PUSH_DEPTH = 0.25
# a band lane's push depth (the owner, after the show of 2026-10-30: band
# routes land far too hot). A lane reads u = band / bands.CEIL, ≈ 0.385 for
# a nominal band, so the `position` row a lane used to land parked the
# param at ~38 % of its throw and threw the base away, and a push at 0.5
# added 0.19 of the throw per band — "each band pushes a third of the
# range". A push of 0.12 about the base adds ≈ 0.05 of the throw per
# nominal band: a shimmer the base shows through, and the depth knob
# takes it up from there
LANE_DEPTH = 0.12
LANE_SCHEME = "lane"        # the analyzer's bands (routing.BUILTIN_LANES[0])


def centred_target(p: Param) -> bool:
    """A continuous range centred on zero, by declaration: no taper, not
    log, lo == -hi (rot.rate.*, rot.phase.*, camera.yaw / pitch / pan.*,
    dream.hue, any effect uniform declared that way). Nothing here reads
    the param's id or group."""
    return (p.kind is Kind.CONTINUOUS and p.taper is None and not p.log
            and p.hi > 0 and p.lo == -p.hi)


def blocked_words(name: str, why: str, verb: str = "map") -> str:
    """`blocked`'s answer, in the one set of words a person reads for it."""
    if why == "invariant":
        return f"{name} is invariant (the meta controller's)"
    return (f"{name} is on the global layer (the meta controller's) — latch SHIFT off to "
            f"{verb} into the patch")


def _table_name(table: Bindings) -> str:
    """Where a meta row lands, as a note says it: the table's file, when it has one."""
    return getattr(table.path, "name", "the meta controller")


def blocked(table: Bindings, source: str) -> str | None:
    """Why no desk row can be learned onto the control `source` names, as
    the table stands: ``"invariant"`` — the meta controller's on both layers (D6)
    — ``"global"`` — nothing is learned while the global layer is up (D5)
    — or None when it can. The one rule `Learn.learn_control` refuses by
    and the on-screen desk asks before a click (`ui_desk.mappable`)."""
    b = Binding(source, "", "abs", layer="preset")
    if table.is_invariant(b):
        return "invariant"
    # the layer up on the device the control is on (plan 27 B2: each MIDI
    # role has its own latch; a table from before a hot reload has one)
    layer_of = getattr(table, "layer_of", None)
    layer = layer_of(b.device or None) if layer_of is not None else table.layer
    if layer == "global":
        return "global"
    return None


# ---- what a loadable patch can show, and what it uses (plan 24 C3) ----
#
# A desk control on a param the loadable patch cannot show is "dead": it moves a
# value nobody sees. `cannot_show` is the one rule, by group, read off the
# loadable patch's own bases (the values a load lands, not this frame's modulation):
#
#   pattern.*, view.pattern, view.pattern_mix   the faces are off (view.faces)
#   view.media_*, view.bmp_alpha                 the faces are off, or nothing wired into
#                                                their layer (`pattern.media`, plan 33 T7)
#   view.points_alpha / view.lines_alpha         points / lines off
#   view.screen_strokes                          points and lines both off
#   fx.mix                                       the effects are off (fx.on)
#   fx.<effect>.<key> (not .on)                  fx.on off, or that effect off
#   dream.<look-back knob>                       no look-back drawn (plan 36 T4: the graph's)
#   dream.<dream knob> (not dream.on)            no dream drawn, or the dream off (dream.on)
#   rot.rate.*, view.plane.*                     rotation is off (view.rotate)
#
# Anything else can always show. tools/desk_coverage.py counts with it, and
# click-to-map (`ranked`) never offers a dead param among a loadable patch's own.

_PATTERN = ("view.pattern", "view.pattern_mix")
_MEDIA = ("view.media_alpha", "view.media_scale", "view.media_mode", "view.media_amp",
          "view.media_rate",      # plan 32: the faces' media channel (was view.bmp_*)
          "view.bmp_alpha")       # …and the factory knob 7's alias of view.media_alpha
_ROTATE = ("rot.rate.", "view.plane.")
# plan 36 T4 (W4): a look-back's knobs (`params.is_lookback_knob`) show while
# the graph draws a look-back; every other `dream.*` is the dream node's,
# shown while a dream is drawn and `dream.on`


def drawn_of(spec) -> frozenset[str] | None:
    """The nodes graph `spec` (a `graph.GraphSpec`) names in its wires —
    a pin as its node (`lookback.echo.3` the look-back) — what decides
    whether a look-back's or the dream's knobs can show (plan 36 T4). None
    with no graph to ask."""
    if spec is None:
        return None
    names = {n for w in spec.all_wires() for n in (w.src, w.node)}
    return frozenset({*names, *(pin_node(n) for n in names if pin_node(n) is not None)})


def _lookback_of(pid: str) -> str:
    """The look-back a look-back knob is of: `dream.2.fade` → `lookback.2`."""
    parts = pid.split(".")
    return "lookback" if len(parts) == 2 else f"lookback.{parts[1]}"


def faces_media(spec, selects=None) -> bool | None:
    """Whether the graph `spec` (a `graph.GraphSpec`) wires a picture into
    the faces' media layer, `pattern.media` — straight, or through a switch
    at its pick (`selects`, `ViewState.switch`) — what `view.media` said
    before plan 33 T7 retired it. None with no graph to ask."""
    if spec is None:
        return None
    return source_into(spec.all_wires(), "pattern.media", selects) is not None


def cannot_show(pid: str, values, media: bool | None = None,
                drawn: frozenset[str] | None = None) -> str | None:
    """Why the loadable patch whose bases are `values` ({id: base}; `.get` is all
    that is asked) cannot show `pid`, in a few words ("faces off",
    "kaleido off"), or None when it can — the rule above. A switch the
    values do not name counts as on. `media`: whether its graph wires a
    picture into the faces' layer (`faces_media`); None (no graph to ask)
    counts as wired — `view.media`, which said it before plan 33 T7, is no
    param any more. `drawn`: the nodes the graph names (`drawn_of`) — a
    look-back's knob shows while its look-back is drawn, the dream's while
    the dream is (plan 36 T4); None (no graph to ask) counts as drawn."""
    def off(sw: str) -> bool:
        v = values.get(sw)
        return v is not None and not bool(v)
    if pid.startswith("pattern.") or pid in _PATTERN:
        return "faces off" if off("view.faces") else None
    if pid in _MEDIA:
        if off("view.faces"):
            return "faces off"
        return "no media channel" if media is False else None
    if pid == "view.points_alpha":
        return "points off" if off("view.points") else None
    if pid == "view.lines_alpha":
        return "lines off" if off("view.lines") else None
    if pid == "view.screen_strokes":
        # the stroke space (plan 26 A2b) moves the edges and the dots only.
        # At camera.zoom 1 it shows nothing either, but that is no rule: a
        # routed zoom makes it live
        both = off("view.points") and off("view.lines")
        return "points and lines off" if both else None
    if pid == "fx.mix":
        return "effects off" if off("fx.on") else None
    if pid.startswith("fx."):
        parts = pid.split(".")
        if len(parts) >= 3 and parts[-1] != "on":
            if off("fx.on"):
                return "effects off"
            name = ".".join(parts[1:-1])
            return f"{name} off" if off(f"fx.{name}.on") else None
        return None
    if is_lookback_knob(pid):
        return ("no look-back" if drawn is not None and _lookback_of(pid) not in drawn
                else None)
    if pid.startswith("dream.") and pid != "dream.on":
        if drawn is not None and "dream" not in drawn:
            return "no dream"
        return "dream off" if off("dream.on") else None
    if pid.startswith(_ROTATE):
        return "rotation off" if off("view.rotate") else None
    return None


def _moved(v, d) -> bool:
    """Is a base `v` off its group default `d`? Numbers within a hair are the same."""
    if isinstance(v, bool) or isinstance(d, bool) or not isinstance(v, (int, float)) \
            or not isinstance(d, (int, float)):
        return v != d
    return abs(float(v) - float(d)) > 1e-9 * max(1.0, abs(float(d)))


# the "uses" tiers, best first: what `ranked` says of each of a loadable patch's params
ROUTED, MOVED, ON, DESKED = "routed", "moved", "on", "on the desk"


def ranked(params: list[tuple[str, str]], values, defaults, routed, on_desk,
           shows=None, media: bool | None = None, drawn: frozenset[str] | None = None
           ) -> tuple[list[tuple[str, str]], list[tuple[str, list[str]]]]:
    """Click-to-map's offer (plan 24 C3): the params this loadable patch uses,
    ranked, then the rest by group. A pure function.

    `params`: (id, group) of every param a desk control may take, in
    registry order. `values`: {id: base} as loaded. `defaults`: {id: its
    group default} for the loadable patch's own params (the patch groups —
    what a load fills an id the file does not name with). `routed`: the
    ids a route or a macro subscriber drives. `on_desk`: the ids a
    patch-layer row already holds. `shows(pid)`: why it cannot show, or
    None (`cannot_show` over `values` and `media` when not given).

    Returns (used, rest). `used` is [(id, why)], in tiers — ``routed`` (a
    route or a macro moves it), ``moved`` (its base is off the group
    default), ``on`` (an effect, the look-back, the faces, the points or
    the lines it belongs to are on, by `cannot_show`'s groups), and last
    ``on the desk`` (already on a control: a second one is seldom what is
    meant) — each tier in registry order. A param the loadable patch cannot show is
    never used. `rest` is every other param as [(group, [id, …])], the
    patch groups first, then the meta controller's, each in registry order."""
    why_not = shows if shows is not None else (
        lambda pid: cannot_show(pid, values, media, drawn))
    tiers: dict[str, list[str]] = {ROUTED: [], MOVED: [], ON: [], DESKED: []}
    rest: dict[str, list[str]] = {}
    for pid, group in params:
        tier = None
        if why_not(pid) is None:
            if pid in on_desk:
                tier = DESKED
            elif pid in routed:
                tier = ROUTED
            elif pid in defaults and _moved(values.get(pid), defaults[pid]):
                tier = MOVED
            elif _switched_on(pid, values, drawn):
                tier = ON
        if tier is None:
            rest.setdefault(group, []).append(pid)
        else:
            tiers[tier].append(pid)
    used = [(pid, why) for why, ids in tiers.items() for pid in ids]
    order = {g: i for i, g in enumerate(PATCH_GROUPS)}
    groups = sorted(rest, key=lambda g: (order.get(g, len(order)), list(rest).index(g)))
    return used, [(g, rest[g]) for g in groups]


def _switched_on(pid: str, values, drawn: frozenset[str] | None = None) -> bool:
    """Is `pid` part of a module `cannot_show` knows that is on — its
    switch named in `values` and set? (A param of no such module: False.)
    Plan 36 T4: a look-back's knob while its look-back is drawn (`drawn`),
    the dream's while the dream is drawn and on."""
    if pid.startswith("pattern.") or pid in _PATTERN or pid in _MEDIA:
        return bool(values.get("view.faces"))
    if pid == "view.points_alpha":
        return bool(values.get("view.points"))
    if pid == "view.lines_alpha":
        return bool(values.get("view.lines"))
    if pid == "view.screen_strokes":
        return bool(values.get("view.points")) or bool(values.get("view.lines"))
    if pid.startswith("fx.") and pid.count(".") >= 2 and not pid.endswith(".on"):
        name = pid.split(".", 1)[1].rsplit(".", 1)[0]
        return bool(values.get("fx.on")) and bool(values.get(f"fx.{name}.on"))
    if is_lookback_knob(pid):
        return drawn is not None and _lookback_of(pid) in drawn
    if pid.startswith("dream.") and pid != "dream.on":
        return bool(values.get("dream.on")) and (drawn is None or "dream" in drawn)
    return False


def clutch_of(source: str) -> str:
    """The gate a room lane's `turn` row lands with: the same hand's closed
    fist, ``hand:right.room.yaw`` → ``hand:right.grab`` (plan 51 O2)."""
    head, _, name = source.partition(":")
    return f"{head}:{name.partition('.room.')[0]}.grab"


def is_auto_clutch(source: str, when: str | None) -> bool:
    """Is `when` the gate a room lane lands with? A row does not say who set it,
    so a person picking that very gate is read as the automatic one."""
    return whole_circle(source) and when == clutch_of(source)


def row_for(source: str, p: Param, when: str | None = None, *,
            centred: bool = False, depth: float | None = None) -> Binding:
    """The row a hand learn makes (plan 18 WP3): its op and depth.

        the target                     a centred axis  a one-sided axis  a band lane  an LFO       an envelope
        continuous, centred on zero    push, depth D   push, depth D     push, L      push, D      push, depth H
        any other continuous param     push, depth D   position, depth 1 push, L      push, D      push, depth H
        an enum, a toggle, a trigger,
        a whole-number param           position, 1     position, 1       position, 1  position, 1  position, 1

    D is `depth`, or `PUSH_DEPTH` when the caller named none; L is
    `depth`, or `LANE_DEPTH`. A band lane (the ``lane`` scheme) and an LFO
    (``lfo``, `lfo.GROUP`) are pushes about the base on any continuous
    target (the owner, after the show of 2026-10-30): a lane reads
    `band / bands.CEIL`, ≈ 0.385 nominal, so as the fader it parked the
    param at ~38 % of its throw and threw the base away, and as a push
    at 0.5 ("Route a lane here…" until now) each band added 0.19 of the
    throw — a third of a centred range's positive half; an LFO's output
    is one-sided (0 … 1) and as the fader swept the whole throw whatever
    the base. An envelope
    (the ``env`` scheme, `envelope.GROUP`) rests at 0 and only rises, so as
    the fader it pinned the param to its minimum between fires (the owner,
    2026-10-24: "they all reduce the base to 0 in between fires no matter
    what I set the base to be"): it is a push about the base instead, H
    the headroom above the base when the row is made, `1 - p.norm`, and
    at least `PUSH_DEPTH` — a full fire reaches the top of the range, and
    between fires the base shows. A push
    carries no `rest` of its own, so it is centred where the axis
    rests, resolved every frame (`Router.rest_of`): a level hand, or
    a height at the bottom, adds nothing and the loadable patch's value shows
    until the hand moves. A discrete target keeps the fader because a
    push of D about a toggle's base never crosses `params.MOD_ON`, and
    about a whole-number param with a short throw (`dream.steps`, 1–3)
    never reaches the next step: the learn would land and do nothing.
    Nothing reads the target's id or group and nothing is refused here: a
    rate-type param lands by the same table as any other. A meta param's row
    (register row 743) is refused where it would land: `Learn.learn_source`
    says so first and `Bindings.add` is the door.

    Every row lands with the default feel, `motion.DEFAULT_ROUTE_FEEL`
    (the named `smooth` spring; the owner, 2026-10-31) — except an
    envelope's, on any target, which keeps `motion=None`: an envelope has
    an attack and a release of its own, and a half-second spring on top
    would blunt a kick-fired hit. A saved row keeps whatever feel it has;
    nothing here rewrites one.

    A hand's room lane (`whole_circle`, plan 51) on a wrapping target is the
    orbit: a `turn` at 1 with no feel, clutched by that hand's fist unless the
    caller names a gate (`clutch_of`). On any other continuous target it is
    the `position` fader at 1 with no feel, centred or not. Depth 1 is what
    makes a palm's turn the target's turn, one for one, and a spring would
    glide across the seam through the whole range."""
    stepped = p.kind is not Kind.CONTINUOUS or p.integer
    if not stepped and whole_circle(source):
        if p.wrap:
            return Binding(source, p.id, TURN_OP, 1.0, when=when or clutch_of(source))
        return Binding(source, p.id, "position", 1.0, when=when)
    env = base_scheme(source.partition(":")[0]) == ENV_SCHEME
    feel = None if env else DEFAULT_ROUTE_FEEL
    if not stepped and env:
        return Binding(source, p.id, "push", max(1.0 - p.norm, PUSH_DEPTH), when=when)
    scheme = base_scheme(source.partition(":")[0])
    if scheme == LANE_SCHEME and depth is None:
        depth = LANE_DEPTH                  # L: a lane's own depth, where D is a hand's
    if not stepped and (centred or centred_target(p)
                        or scheme in (LANE_SCHEME, lfo.GROUP, PAIR_SCHEME)):
        d = PUSH_DEPTH if depth is None else float(depth)
        return Binding(source, p.id, "push", d, when=when, motion=feel)
    return Binding(source, p.id, "position", 1.0, when=when, motion=feel)


def _steps_on(x: Binding, b: Binding, bare: tuple[str, ...]) -> bool:
    """Is `x` a pair's `step` row (plan 56) of `b`'s pad with a pole among
    `bare` (``hat:N``)? A row on that button, then, in a button learn's eyes."""
    if x.scheme != PAIR_SCHEME or x.op != "step" or x.device != b.device:
        return False
    poles = pair_poles(":".join(x.parts))
    return poles is not None and any(pole.source in bare for pole in poles)


def _split_row(table: Bindings, x: Binding, bare: tuple[str, ...]) -> list[Binding]:
    """A pair's `step` row `x` goes from the poles `bare`, and the pole they do
    not take keeps moving as it did, as a row of its own with everything else `x`
    had (its gate, its scale). Returns those rows."""
    left = []
    table.remove(x)
    for pole, sign in zip(pair_poles(":".join(x.parts)) or (), (1, -1), strict=False):
        if pole.source not in bare:
            scheme, _, name = pole.source.partition(":")
            row = replace(x, source=f"{qualified(scheme, x.device)}:{name}", value=sign * x.value)
            table.add(row)
            left.append(row)
    return left


def _split_pairs(table: Bindings, b: Binding, bare: tuple[str, ...]) -> tuple[list, list]:
    """A button learn takes the poles `bare`: each pair's `step` row on one
    (`_steps_on`) splits (`_split_row`). Returns (the pair rows gone, the rows
    left behind)."""
    gone, left = [x for x in table.bindings if _steps_on(x, b, bare)], []
    for x in gone:
        left += _split_row(table, x, bare)
    return gone, left


# ---- a pair that overlaps a mapping asks first (register row 754) ----

KEEP_BOTH, TAKE_OVER, CANCEL = "keep both", "take over", "cancel"
# where a meta row's step is: the stack, not a promise of the next ⌘Z (a stack just
# come to may refuse until a change is made on it, row 753). `ui.META_SECTIONS`
META_UNDO = "undo it on the meta controller's stack: mouse over OUTPUT, AUDIO, ANALYZER or HANDS"
DECK_UNDO = "undo the route taken on this deck's stack"


def pole_rows(table: Bindings, b: Binding, skip: Iterable[Binding] = ()) -> list[Binding]:
    """The mappings `b` would land beside: a row of its own on either pole, or
    another pair's sharing one, that would still stand once `b` lands. Empty when
    `b` is on no pair or is switched off, since it acts on nothing. The same pair
    on any param is one lane read twice, not a pole's mapping (row 754). A row
    switched off acts on nothing. A performer on `b`'s own target is the referee's
    question: `b` replaces it whichever way this one is answered. `skip`: what the
    road moves anyway."""
    poles = pair_poles(":".join(b.parts)) if b.scheme == PAIR_SCHEME and b.enabled else None
    if poles is None:
        return []
    bare = {pole.source for pole in poles}
    skip = tuple(skip)

    def on_pole(x: Binding) -> bool:
        if x.scheme == PAIR_SCHEME:
            theirs = pair_poles(":".join(x.parts))
            return theirs is not None and any(pole.source in bare for pole in theirs)
        return x.bare in bare
    return [x for x in table.bindings
            if x.enabled and x.device == b.device and x.source != b.source and on_pole(x)
            and not (b.is_performer and x.is_performer and x.target == b.target)
            and not any(x is y for y in skip)]


@dataclass
class PairAsk:
    """`new` asks for a pair whose poles already have rows. Nothing has changed
    yet. `land` is the road's landing once answered, which `settle_pair` runs;
    `skip` is what that road moves anyway; `replaced` is the table's count of its
    routes being replaced when asked (`stale`)."""

    table: Bindings
    new: Binding
    land: Callable[[], object]
    skip: tuple[Binding, ...] = ()
    replaced: int = 0

    @property
    def rows(self) -> list[Binding]:
        """What is on the poles now: read when drawn and when answered."""
        return pole_rows(self.table, self.new, self.skip)

    @property
    def stale(self) -> bool:
        """Has what it asked about gone from under it? A load or an undo replaced
        the routes, so the answer would land in another patch's table; or nothing
        is on the poles now, so there is nothing to consent to."""
        return self.table.routes_replaced_n != self.replaced or not self.rows


def withdrawn_words(ask: PairAsk) -> str:
    return f"nothing landed: the mappings changed while {row_words(ask.new)} asked"


def propose_row(table: Bindings, new: Binding, land: Callable[[], object],
                answered: Callable[[], object] | None = None, moving: Binding | None = None):
    """The one door for a row a person makes (register row 754). Lands it (returns
    what `land` returns), or holds it and returns a `PairAsk` when it overlaps a
    mapping, with `answered` the landing that runs on an answer (default `land`:
    the road's own second question has been asked by then). `moving`: the row in
    the table being re-pointed to be `new`; its own source again asks nothing."""
    skip = () if moving is None else (moving,)
    if (moving is None or moving.source != new.source) and pole_rows(table, new, skip):
        return PairAsk(table, new, answered or land, skip, table.routes_replaced_n)
    return land()


def _label(pid: str, reg: Registry | None) -> str:
    p = reg.get(pid) if reg is not None else None
    return (p.label if p is not None else "") or pid


def _row_says(x: Binding, reg: Registry | None) -> str:
    """"d-pad up moves Brightness", with whose row it is."""
    whose = "the meta controller's, for every patch" if is_meta_row(x) else "this patch's"
    return f"{row_words(x)} moves {_label(x.target, reg)} ({whose})"


def pair_lines(ask: PairAsk, reg: Registry | None = None) -> list[str]:
    """The question's words: which control is mapped, and to what; which row asks."""
    return [*(_row_says(x, reg) for x in ask.rows),
            f"{row_words(ask.new)} asks to move {_label(ask.new.target, reg)}."]


def settle_pair(ask: PairAsk, choice: str, reg: Registry | None = None) -> str:
    """The answer, in words. **Keep both** lands the row and both act. **Take
    over** lands it, then the rows on its poles go, read now; a pair's `step` row
    leaves its other pole moving (`_split_row`). **Cancel** lands nothing.

    One step on each stack the answer changes, and only those: the new row's
    layer, and a row taken from the other layer on that layer's stack (a meta
    row: `undo.push_meta`, restored through `MetaTable.set_rows`, which writes
    the file). No stack reaches into another, so the words say where each is. The
    meta push comes last: by the latch (row 753) only the stack a person's change
    ended on can take it back at once, and a meta row is the one they cannot
    simply delete again from where they are."""
    if choice not in (KEEP_BOTH, TAKE_OVER, CANCEL):
        raise ValueError(f"no such answer {choice!r}")
    table, new = ask.table, ask.new
    pair = row_words(new)
    if choice == CANCEL:
        return f"nothing landed: {pair} → {new.target}"
    if ask.stale:
        return withdrawn_words(ask)
    why = table.refusal(new)             # before any push: a push moves the focus (row 753)
    if why is not None:
        return f"nothing landed: {why}"
    rows = ask.rows
    gone = rows if choice == TAKE_OVER else []
    meta = is_meta_row(new) or any(is_meta_row(x) for x in gone)
    taken_route = any(not is_meta_row(x) for x in gone)
    label = f"pair {new.target}"
    if not is_meta_row(new) or taken_route:
        undo.push(label)
    if meta:
        undo.push_meta(label)
    try:
        ask.land()                       # first: a refusal leaves the poles' rows alone
    except ValueError as e:              # not the referee's, asked above: a guard for the poles
        return f"nothing landed: {e}"
    bare = tuple(pole.source for pole in pair_poles(":".join(new.parts)) or ())
    kept: list[Binding] = []
    for x in gone:
        if _steps_on(x, new, bare):
            kept += _split_row(table, x, bare)
        else:
            table.remove(x)
    if meta:
        table.write()                    # once: the landing leaves the file to this
    where = (f"; {META_UNDO}" if meta else "") + (
        f"; {DECK_UNDO}" if meta and taken_route else "")
    if choice == KEEP_BOTH:
        return (f"both act: {pair} → {new.target}, and "
                f"{', '.join(row_words(x) for x in rows)} as it was{where}")
    return (f"the pair took over: {pair} → {new.target}; let go: "
            + ", ".join(_row_says(x, reg) for x in gone)
            + "".join(f"; {x.target} keeps {x.describe()}" for x in kept) + where)


def land_moved(b: Binding, old_source: str, p: Param | None) -> None:
    """A row just re-pointed lands as `row_for` would when a room lane or a
    `turn` is in it (any other row keeps its op, depth and feel, as it always
    did): a clutch that was the old hand's fist follows to the new one, a gate
    someone picked stays; a `turn` on a target that no longer wraps or a source
    that is no circle becomes that target's row; a turn stays at its depth."""
    if p is None or (b.op != TURN_OP and not whole_circle(b.source)):
        return
    new = row_for(b.source, p, None if is_auto_clutch(old_source, b.when) else b.when)
    if b.op == new.op == TURN_OP:
        b.when = new.when
        return
    b.op, b.value, b.when, b.motion, b.rest = new.op, new.value, new.when, new.motion, new.rest


def move_route(table: Bindings, reg: Registry, b: Binding, *, source: str | None = None,
               target: str | None = None):
    """`Bindings.move_route`, and the row landing as `row_for` would (`land_moved`)."""
    old = b.source
    got = table.move_route(b, source=source, target=target)
    land_moved(b, old, reg.get(b.target))
    return got


class Learn:
    """The armed param and the question the referee left for the panel."""

    pair_ask: PairAsk | None = None      # on the class: a `Learn` from before a hot reload

    # told each row a learn makes (plan 55: `DeviceRegistry.mapped`, so a controller
    # mapped on another deck moves there); None: nobody asks
    mapped = None

    def __init__(self, reg: Registry, table: Bindings, lane=None, devices=None):
        self.reg = reg
        self.table = table
        # the device registry (devices.DeviceRegistry, plan 27 B2), asked
        # what can be armed (`wants`); None: today's meta controller (BARE_WANTS)
        self.devices = devices
        # the router's `lane` (source → (scheme, index)), so one hand axis
        # named two ways — `hand:7` in an older loadable patch, `hand:right.y` from
        # a learn — is one axis here too (decision register row 20); None:
        # sources compare as strings
        self.lane = lane
        self.learning: str | None = None
        self.want: str | None = None   # what may complete `learning` (`wants`); None: anything
        self.control: str | None = None    # the picked desk control's source; None: none
        self.pending: tuple[Binding, Binding] | None = None
        self.held = False       # plan 40 T3: a spawn's sheet is up — nothing completes a learn
        self.last = ""        # what the last learn did, for the status lines
        self.refused = False    # …and whether it was a refusal (drawn as a warning)
        self.said_n = 0         # how many times `last` was set: the same words twice are two

    def same_source(self, a: str, b: str) -> bool:
        """Do two source addresses read the same lane — the same string,
        or a number and a name the router resolves to one lane?"""
        if a == b:
            return True
        lane = getattr(self, "lane", None)       # a Learn from before a hot reload: None
        if lane is None:
            return False
        la = lane(a)
        return la[1] >= 0 and la == lane(b)

    def wants(self) -> tuple[str, ...]:
        """What a learn may wait for on this rig, in offer order: "desk"
        (the on-screen desk, and every MIDI role), then each listed
        device's (`DeviceRegistry.wants`: the pad's "pad", the hands'
        "hand:left" / "hand:right", a new device's role). With no registry,
        BARE_WANTS."""
        devs = getattr(self, "devices", None)
        if devs is None:
            return BARE_WANTS
        return tuple(dict.fromkeys((DESK, *devs.wants())))

    def said(self, text: str) -> None:
        """What a learn that landed (or was kept) did, for the status lines."""
        self.last, self.refused = text, False
        self.said_n = getattr(self, "said_n", 0) + 1     # the footer shows each saying once

    def refuse(self, why: str) -> None:
        """A learn that may not land: nothing changes, `last` says why."""
        self.last, self.refused = why, True
        self.said_n = getattr(self, "said_n", 0) + 1

    # ---- arming ----

    def arm(self, pid: str | None, want: str | None = None) -> None:
        """Arm (or cancel with None). `want` is what may complete it — one
        of `wants()`, or None for anything. A learn the prompt hasn't
        answered yet is forgotten: the new one is what the performer means
        now. Arming starts clean: an earlier refusal is no longer this
        learn's (`refused` while armed means *this* learn was refused and
        still waits), and `armed_n` counts the arms, so an adapter that
        keeps something per learn (the hands' baseline) can tell a re-arm
        of the same param from the learn it already knew."""
        wants = self.wants()
        if want is not None and want not in wants:
            raise ValueError(f"no such want {want!r}; one of {', '.join(wants)}")
        self.learning = pid
        self.want = want if pid is not None else None
        self.pending = None
        if pid is not None:
            self.refused = False
            self.control = None          # arming a param lets a picked control go
        self.pair_first = None           # plan 56: no pole pressed yet
        self.pair_ask = None             # row 754: a new arm forgets it, as `pending`
        self.armed_n = getattr(self, "armed_n", 0) + 1

    def hold(self, on: bool = True) -> None:
        """Plan 40 T3: while a spawn's conflict sheet is up (D3) no source
        completes the armed learn — `accepts` says no to every one, so the
        hands, a desk control, a pad or an OSC fader learn nothing, as
        while the Replace / Keep prompt is up — and the learn stays armed
        for after (`hold(False)`, the sheet answered)."""
        self.held = bool(on)

    def take(self) -> str | None:
        """The armed id, cleared — an adapter about to complete the learn
        calls this first so nothing else can complete it too."""
        pid, self.learning = self.learning, None
        self.want = None
        self.pair_first = None
        return pid

    def accepts(self, source: str) -> bool:
        """May this source complete the armed learn? False when nothing
        is armed. want None: any source. "desk": a cc / note / pitch
        source, from any MIDI device (a qualified ``cc@launch:0:7`` too:
        plan 27 B2). "hand:left": a source that starts "hand:left." (an
        axis or a switch of that hand, by name). "pad": a gamepad button,
        the D-pad or an axis (PAD_SCHEMES). A device's role (a want with no
        ``:``): a source under that scheme. A modifier's output lane
        (``mod:<n>``, plan 28 N1) is a continuous source like a hand's
        axis: it completes a learn armed for anything, or for "mod", and
        never a desk, pad or hand one."""
        if getattr(self, "learning", None) is None:
            return False
        if getattr(self, "held", False):         # plan 40 T3: a sheet is up (`hold`)
            return False
        want = getattr(self, "want", None)       # a Learn from before a hot reload: None
        if want is None:
            return True
        if source.partition(":")[0] == modifiers.SCHEME:
            return want == modifiers.SCHEME
        if want == DESK:
            return Binding(source, "").is_midi
        if want in PAIR_WANTS:               # a pole, or the pair a port names (plan 56)
            return base_scheme(source.partition(":")[0]) in ("pad", "hat", PAIR_SCHEME)
        if want == "pad":                    # any pad's: ``pad@p2:S`` too (plan 27 B6)
            return base_scheme(source.partition(":")[0]) in PAD_SCHEMES
        if ":" not in want:
            # a role: a source under that scheme (an OSC role's), or one
            # qualified with it (``pad@p2:S`` completes "p2", plan 27 B6)
            return (source.partition(":")[0] == want
                    or Binding(source, "").device == want)
        return source.startswith(f"{want}.")

    # ---- a desk control completes it ----

    def learn_control(self, source: str, profile=None) -> bool:
        """A desk control completes the armed learn: a patch-layer row
        into the loaded patch (plan 13 §3.3). True when it landed.

        The one road onto the desk (plan 17 WP2): the MIDI adapter calls
        it with the message it received, the on-screen desk with the
        control clicked — so it needs no adapter. `profile` is the device's
        module, duck-typed (`is_relative`, `feedback_for`, `named`), for
        the op, the feedback and the control's name; None gives a plain
        `abs` row named by `Binding.describe`.

        It binds the param as armed. Refused, with the reason in `last`,
        nothing changed and **the learn still armed**, on an invariant
        control (D6) and while the global layer is up (D5): both are the
        meta controller's. A meta param (row 743) is refused whatever the control:
        this row would be the loadable patch's, and no patch row may drive one. A
        learn armed for the desk is then over, since no control can land it;
        a bare arm still waits for a pad button, which can.
        Otherwise the row replaces every patch-layer row on the control
        (an any-channel row on it included, `Binding.overlaps`) and the
        param's previous patch-layer row in the same role
        (`Bindings.bind`); no file is written. One undo step. The table's
        `redraw_serial` moves, so an adapter redraws the desk: the
        replaced rows' controls go dark and the new row's ring is sent."""
        if not self.accepts(source):     # nothing armed, or armed for a hand: not the desk's
            return False
        pid = self.learning
        p = self.reg.get(pid) if pid is not None else None
        if p is None:
            self.take()                  # an id the registry lacks can never land
            return False
        if pid == SAVE_PARAM:
            self.refuse(SAVE_REFUSAL)
            return False
        table = self.table
        b = Binding(source, pid, "abs", layer="preset")

        def named(x: Binding) -> str:
            name = getattr(profile, "named", None) or getattr(profile, "control_name", None)
            return (name(x.bare) if name is not None else None) or x.describe()
        why = blocked(table, source)
        if why == "invariant":
            self.refuse(f"{blocked_words(named(b), why)} — not learned")
            return False
        if why == "global":
            self.refuse(blocked_words(named(b), why, verb="learn"))
            return False
        why = meta_refusal(pid)          # (only now: a row on these two is the meta controller's)
        if why is not None:
            if self.want == "desk":
                self.take()
            road = f"; {PER_DECK_ROAD}" if is_per_deck_meta_id(pid) else ""
            self.refuse(f"{why} — not learned{road}")
            return False
        kind, number = b.kind, b.number
        if pid in HELD_ONLY and kind != "note":
            self.refuse(f"{pid} is held: it takes a button, not {named(b)}")
            return False
        if kind == "cc":
            if profile is not None and profile.is_relative(number):
                b.op = "rel"
            elif p.kind is Kind.TRIGGER:
                b.op = "toggle"
        elif kind == "note":
            b.op = "momentary" if pid in HELD_ONLY else "toggle"
        b.feedback_from(profile)
        self.take()
        undo.push(f"learn {pid}")                    # one undo step (undo.py, plan 15)
        gone = table.bind(b, write=False)            # the patch rows it replaced
        self._mapped(b)
        table.redraw_serial = getattr(table, "redraw_serial", 0) + 1
        glyph = getattr(profile, "glyph", None)
        let_go = list(dict.fromkeys(
            (glyph(x.bare) if glyph is not None else None) or named(x)
            for x in gone if not x.overlaps(b)))
        under = table.under_node_mode(b)
        self.said(f"learned {pid} ← {named(b)} (into the patch)"
                  + (f"; {', '.join(let_go)} let go" if let_go else "")
                  + ("; under node mode until that desk leaves its node" if under else ""))
        return True

    # ---- click a control, then a param ----

    def pick(self, source: str | None) -> None:
        """Pick a desk control (None lets go). Arming a param lets it
        go; picking a control cancels an armed learn. A pick changes no
        table and is no undo step."""
        if source is not None and getattr(self, "learning", None) is not None:
            self.arm(None)
        self.control = source

    def map_picked(self, pid: str, profile=None) -> bool:
        """The picked control takes this param: arm(pid, "desk"), then
        learn_control(control). True when it landed, and the pick is then
        over. When it did not, the control is still picked, no learn is
        left armed behind it, and `last` says why: an invariant control or
        the global layer in the knob learn's words, or a param the
        registry lacks. (Like any arm, it forgets a held Replace / Keep
        question.)"""
        source = getattr(self, "control", None)
        if source is None:
            return False
        self.arm(pid, "desk")                # (lets the pick go: `source` holds it)
        landed = self.learn_control(source, profile)
        if not landed:
            said = self.refused              # learn_control's own refusal, if it made one
            self.arm(None)
            self.control = source
            if not said:
                self.refuse(f"{pid}: no such param — nothing mapped")
        return landed

    # ---- a gamepad button completes it ----

    def learn_pad_button(self, source: str) -> bool:
        """A gamepad button or D-pad direction (``pad:S``, ``hat:N``)
        completes the armed learn: a button row like a desk note's — a
        trigger fires, a toggle or an enum toggles (the enum steps to its
        next choice), and a fader steps one detent: down for the D-pad's
        DOWN and LEFT, up for anything else (one detent at a time, as the
        factory's D-pad rows on brightness; their size is edited in the
        file). True when it landed.

        Pad rows are the meta controller's, as the factory's are (`padmap`): the
        row goes into `bindings.json`, which is written now, and is no undo
        step — nor in any loadable patch. It replaces every row on that button; the
        param's other controls stay.

        Armed for a pair (plan 56), the press is one of its poles instead
        (`_pair_pole`)."""
        if not self.accepts(source):
            return False
        if getattr(self, "want", None) in PAIR_WANTS:
            return self._pair_pole(source)
        pid = self.learning
        p = self.reg.get(pid) if pid is not None else None
        if p is None:
            self.take()
            return False
        if pid == SAVE_PARAM:
            self.refuse(SAVE_REFUSAL)
            return False
        if p.kind is Kind.TRIGGER:
            op, value = "fire", 0.0
        elif p.kind is Kind.CONTINUOUS:
            down = Binding(source, pid).bare in ("hat:S", "hat:W")   # any pad's
            op, value = "step", (-1.0 if down else 1.0)
        elif pid in HELD_ONLY:
            op, value = "momentary", 0.0
        else:
            op, value = "toggle", 0.0
        self.take()
        table = self.table
        b = Binding(source, pid, op, value)
        gone = [x for x in table.bindings if x.source == source]
        for x in gone:
            table.remove(x)
        _, kept = _split_pairs(table, b, (b.bare,))
        table.add(b)
        table.write()
        self._mapped(b)
        let_go = ", ".join(dict.fromkeys(x.target for x in gone if x.target != pid))
        keeps = "".join(f"; {x.target} keeps {x.describe()}" for x in kept)
        self.said(f"learned {pid} ← {b.describe()} (into {_table_name(table)})"
                  + (f"; {let_go} let go" if let_go else "") + keeps)
        return True

    # ---- two presses complete it (plan 56) ----

    def _pair_pole(self, source: str) -> bool:
        """A press while armed for a pair: the first is the + pole, and the
        learn waits; the second, another control of the same pad, is the −
        pole, and the pair lands (`learn_pair`). A press of the first again
        is nothing. True: the press was the learn's, whatever it did."""
        from .pads.models import pole_name
        b = Binding(source, "")
        name = pole_name(source)
        first = self.__dict__.get("pair_first")
        if first is None:
            self.pair_first = source
            self.said(f"{name} is the + pole: now press the − pole")
            return True
        was = Binding(first, "")
        if first == source:
            return True
        if was.device != b.device:
            self.refuse("a pair is two controls of one pad: press the − pole on the same pad")
            return True
        return self.learn_pair(pair_address(pole_name(first), name, b.device))

    def learn_pair(self, source: str) -> bool:
        """The pair `source` (``pair:hat.N/hat.S``) completes the armed learn, by
        the want's model. "pair": a `step` row at one detent each way, the
        meta controller's like any pad button row: `bindings.json` is written, and a
        step on the meta stack. Rows on either pole ask first (row 754). "pair (spring)": a
        route through `learn_source`, into the loadable patch as a stick's; a whole-
        number or enum target takes the step row, since a lane resting at 0.5
        would park it mid-throw (a GRAPH cable comes here for the same reason,
        `graphview.Edit.connect_value`). A toggle or a trigger has no two directions:
        refused, and the learn is over. True when it was the learn's."""
        pid = self.learning
        p = self.reg.get(pid) if pid is not None else None
        if p is None:
            self.take()
            return False
        if p.kind in (Kind.TOGGLE, Kind.TRIGGER):
            self.take()
            self.refuse(f"{p.label or pid} has no two directions: a pair moves along a range "
                        "— not learned; Learn pad puts it on one button")
            return True
        table = self.table
        b = Binding(source, pid, "step", 1.0)
        if pair_poles(":".join(b.parts)) is None:
            self.take()
            self.refuse(f"{source} names no two controls of a pad — not learned")
            return True
        if self.want == PAIR_SPRING_WANT and p.kind is Kind.CONTINUOUS and not p.integer:
            self.learn_source(source, centred=True)
            return True
        self.take()

        def land() -> None:
            self._land_step(b)
            table.write()
            self.said(f"learned {pid} ← {b.describe()} "
                      f"(into {_table_name(table)}); {META_UNDO}")
        self._ask_pair(propose_row(table, b, land, lambda: self._land_step(b)))
        return True

    def _land_step(self, b: Binding) -> None:
        """A pair's `step` row into the table, the meta controller's like any pad
        button row; the caller writes the file, once. The same pair on the same
        param again replaces itself; every other row is `settle_pair`'s to take or
        to leave."""
        undo.push_meta(f"learn pair {b.target}")
        table = self.table
        for x in [x for x in table.bindings
                  if x.source == b.source and x.target == b.target and x.op == "step"]:
            table.remove(x)
        table.add(b)
        self._mapped(b)

    def _ask_pair(self, asked) -> None:
        """What `propose_row` returned: a question is held for the panel (row 754),
        the table untouched; a row that landed has nothing to hold."""
        if isinstance(asked, PairAsk):
            self.pair_ask = asked
            self.said(f"{row_words(asked.new)} overlaps a mapping: answer the question")

    # ---- a sink port takes it (plan 27 B3) ----

    def sinks(self) -> tuple:
        """The meta controller's sink ports (devices.Port: `address` ``<role>:<channel>``,
        `label`), in list order — what "Learn sink ▸" offers; none without
        a device registry."""
        devs = getattr(self, "devices", None)
        ports = getattr(devs, "sink_ports", None)
        return tuple(ports()) if ports is not None else ()

    def learn_sink(self, pid: str, port: str) -> Binding | None:
        """Send `pid` out on the sink port `port` (``bridge:3``): a sink row
        ``param:<pid> → <port>`` into the meta controller's table, written to
        `bindings.json` now — sinks are meta controller (D1 / D9), so no undo step and
        no loadable patch dirt, like a pad learn. The row takes the port from
        whatever sent on it before (one source per port); the param may go
        out on several ports. Never a Replace / Keep question: a sink row
        is not a performer. Refused, with the reason in `last` and nothing
        changed, for an id the registry lacks, a trigger (it has no value
        to send) or a port that is not ``<role>:<channel>``. Returns the
        row, or None. Arms nothing: an armed learn stays as it was."""
        p = self.reg.get(pid)
        if p is None:
            self.refuse(f"{pid}: no such param — nothing sent")
            return None
        if p.kind is Kind.TRIGGER:
            self.refuse(f"{p.label or pid} is a trigger — it has no value to send")
            return None
        if parse_sink(port) is None:
            self.refuse(f"{port!r} is not a sink port (<role>:<channel>) — nothing sent")
            return None
        table = self.table
        b = Binding(f"param:{pid}", port, SINK_OP)
        gone = [x for x in table.bindings if x.is_sink and x.target == port]
        if any(x.source == b.source and x.enabled for x in gone) and len(gone) == 1:
            self.said(f"{pid} already goes out on {port}")
            return gone[0]
        for x in gone:
            table.remove(x)
        table.add(b)
        table.write()
        was = ", ".join(dict.fromkeys(x.source for x in gone if x.source != b.source))
        self.said(f"sent {pid} → {port} (into {_table_name(table)})"
                  + (f"; {was} let go" if was else ""))
        return b

    # ---- a source completes it ----

    def target_for(self, pid: str) -> Param | None:
        """The param a route for `pid` must name: the alias's band, else
        itself; None when the registry has no such id."""
        p = self.reg.get(pid)
        if p is None:
            return None
        real = getattr(self.reg, "real", None)
        return real(p) if real is not None else p

    def routable(self, target: Param | None) -> bool:
        """Can a route land on `target`? What an adapter asks before it reads
        an axis for a learn (`gamepad.learn_from`, `osc`): on a param no route
        can take, drift on a stick must not reach `learn_source` and end a
        learn a button could still land."""
        return target is not None and target.modulatable

    def learn_source(self, source: str, when: str | None = None, *,
                     centred: bool = False, depth: float | None = None) -> None:
        """An adapter completes the learn with one of its own sources
        (hands/core.py: ``hand:right.pitch``, by name): a route through
        the Router like every route, with no pickup and no device
        feedback — a `push` about the param's base or the `position`
        fader, by `_row`'s table. `centred` says the source rests in the
        middle of its travel (a hand's roll; not its height) and `depth`
        is the depth a push lands with (the hands pass
        `hands.learn_depth`; None: `PUSH_DEPTH`). `when` gates the row on
        a second source (a pinch held while learning), so the row only
        acts while that reads on.

        A learned axis drives one param: learning it onto another *moves*
        it (its other performer rows go, whatever their op — `_place`),
        and learning it again onto the same param only refreshes the gate
        (the row's op and depth, a loadable patch's or one tuned on ROUTING,
        stay). If the param already has a
        different performer the learn is held in `pending` for the panel's
        prompt (`resolve_pending`) — the table untouched until it answers —
        rather than taking the target or being lost. `learning` is cleared
        first, so the hands adapter, which keys off it, cannot fire again.

        A meta param (register row 743: ``master.gain``) is refused with a line
        the performer can read in `last`, the table untouched, in the rule's
        words: a route is a loadable patch's, and no patch row may drive one.
        Any other target that is not modulatable (`Param.modulatable`: a patch's
        setting such as ``ghost.guide``) is refused the same way in its own: the
        panel never offers Learn hand there, and this is the door's own check.
        """
        if not self.accepts(source):     # nothing armed, or armed for something else
            return
        pid = self.take()
        if pid is None:
            return
        p = self.target_for(pid)
        if p is None:
            return
        why = meta_refusal(p.id)
        if why is not None:
            self.refuse(f"{why} — not learned")
            return
        if not p.modulatable:
            # a setting of the patch's no performer may drive (ghost.guide):
            # a route on it would sit dormant, so none is made. The learn
            # is over — no hand can ever complete it — and nothing changed
            if Binding(source, p.id).scheme in ("axis", PAIR_SCHEME):     # any pad's (plan 27 B6)
                self.refuse(f"{p.label} can't follow a stick (not modulatable) "
                            "— not learned; Learn pad with a button puts it on one")
                return
            self.refuse(f"{p.label} can't follow a hand (not modulatable) "
                        "— not learned; Learn desk puts it on a button")
            return
        b = self._row(source, p, when, centred=centred, depth=depth)
        cur = self.table.owner(p.id)
        if cur is not None and self.same_source(cur.source, source):
            undo.push(f"learn {p.id}")               # one undo step (undo.py, plan 15)
            cur.when = when                          # the same axis again: no move
            self._mapped(cur)
            self.said(f"learned {p.id} ← {cur.describe()} (into the patch)")
            return

        def land() -> None:
            if cur is not None:
                self.pending = (b, cur)
                self.said(f"{Owned(cur, b)} — replace?")
                return
            self._place(b)
        self._ask_pair(propose_row(self.table, b, land, lambda: self._place(b)))

    def _row(self, source: str, p: Param, when: str | None, *,
             centred: bool = False, depth: float | None = None) -> Binding:
        """The row a hand learn makes (`row_for`, the one table — the GRAPH
        page's cable into a `mod` port makes the same row, plan 28 N3)."""
        return row_for(source, p, when, centred=centred, depth=depth)

    def resolve_pending(self, replace: bool) -> Binding | None:
        """The prompt's answer to a held learn: *Replace* swaps the target's
        performer for the learned row (into the loaded patch, no file
        written); *Keep* leaves the table as it was. Returns the row now in
        the table, or None."""
        if self.pending is None:
            return None
        new, old = self.pending
        self.pending = None
        if not replace:
            self.said(f"kept {old.describe()} on {old.target}")
            return None
        self._place(new)
        return new

    def _mapped(self, b: Binding) -> None:
        if self.mapped is not None:
            self.mapped(b)

    def _place(self, b: Binding) -> None:
        """The learned row into the table: the axis's other push / position
        rows go first, whatever their op and switched on or off (one axis,
        one param; plan 18 fork 7 — the status line names the params they
        were on; a switched-off twin on this very target goes too, so the
        table never holds the route twice), then `replace_owner` — the
        one door
        onto a target, which reads the owner *now* (a free target takes the
        row; the prompt's Replace removes whoever holds it at this moment,
        not whoever did when the question was asked). A route of the
        loaded patch's: no file is written (plan 13 §3.3). One undo step
        (undo.py): the rows it took out come back with a Ctrl+Z."""
        undo.push(f"learn {b.target}")
        table = self.table
        gone = [x for x in table.of(b.scheme)
                if x.op in MOD_OPS and self.same_source(x.source, b.source)]
        for x in gone:
            table.remove(x)
        table.replace_owner(b)
        self._mapped(b)
        frm = ", ".join(dict.fromkeys(x.target for x in gone if x.target != b.target))
        self.said(f"learned {b.target} ← {b.describe()} (into the patch"
                  + (f"; moved from {frm})" if frm else ")"))

    # ---- unbind ----

    def bound(self, ids) -> tuple[list[Binding], list[Binding], list[Binding]]:
        """What is bound to a param: (the loaded patch's desk rows, its
        routes, the meta controller's MIDI rows). `ids` as for `unbind`. The first
        two are what `unbind` may remove; the third it never does."""
        return bound(self.table, ids)

    def unbind(self, ids, *, desk: bool = True, routes: bool = True, name=None) -> list[Binding]:
        """Remove what is bound to a param, in the loaded preset: its
        patch-layer desk rows (`desk`) and its routes (`routes`). `ids` is
        the drawn param's id and the real one's (an alias and its band; one
        id when they are the same). Returns the rows removed.

        A desk row goes through `Bindings.unbind` (it bumps
        `redraw_serial`: an adapter redraws and the control goes dark, D8);
        a route — any scheme, enabled or not — through `Bindings.remove`,
        its depth subscribers with it. No file is written: the edit is the
        loaded patch's (plan 13 §3.3). One undo step, pushed once and only
        when something goes. `name(b)` gives each row's words for the
        message; without it, `Binding.describe()`. A meta row is never
        removed: with nothing else to remove, that is a refusal."""
        ids = _ids(ids)
        if not ids:
            return []
        real = ids[-1]
        name = name if name is not None else Binding.describe
        mine, routed, meta_rows = self.bound(ids)
        gone = (mine if desk else []) + (routed if routes else [])
        if not gone:
            if desk and meta_rows:
                b = meta_rows[0]
                where = "on the global layer" if b.layer == "global" else "invariant"
                self.refuse(f"{name(b)} → {b.target} is {where} (the meta controller's, "
                            "edited in bindings.json) — not unbound")
            return []
        undo.push(f"unbind {real}")                  # one undo step (undo.py, plan 15)
        gone = []
        if desk:
            for pid in ids:
                gone += self.table.unbind(pid)       # what the table took out
        if routes:
            for b in routed:
                self.table.remove(b)
            gone += routed
        # a question held against a row that just went has nothing to ask
        if self.pending is not None and any(self.pending[1] is g for g in gone):
            self.pending = None
        names = [name(b) for b in gone]
        told = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
        self.said(f"unbound {real} from {told}")
        return gone


def sinks_of(table: Bindings, ids) -> list[Binding]:
    """The sink rows that send a param out (plan 27 B3), enabled or not:
    the meta controller's, listed by the param's menu, never removed by Unbind."""
    ids = _ids(ids)
    return [b for b in table.bindings
            if b.is_sink and b.source.partition(":")[2] in ids and b.scheme == "param"]


def _ids(ids) -> tuple[str, ...]:
    """One id or several, as a tuple with no repeats, in order."""
    return (ids,) if isinstance(ids, str) else tuple(dict.fromkeys(ids))


def bound(table: Bindings, ids) -> tuple[list[Binding], list[Binding], list[Binding]]:
    """`Learn.bound` over any table (the panel's menu lists from it with
    or without a learn object, so its lines are what Unbind removes):
    (patch-layer desk rows, routes, the meta controller's MIDI rows) on `ids`. A
    route is a performer row from a continuous source — never a MIDI row,
    whatever its op, so a meta row can not come back as a "route"."""
    ids = _ids(ids)
    midi = [b for b in table.bindings if b.is_midi and b.target in ids]
    routes: list[Binding] = []
    for pid in ids:
        routes += [b for b in table.routes_to(pid)
                   if not b.is_midi and not any(b is x for x in routes)]
    return ([b for b in midi if b.layer == "preset"], routes,
            [b for b in midi if b.layer != "preset"])
