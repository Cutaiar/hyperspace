"""Learn — the one armed param, shared by every adapter that can complete it.

Right-click → Learn arms a param id here, with what the learn waits for
(`want`, plan 17 WP2): **Learn desk** arms ``"desk"``, **Learn hand ▸
left / right** arms ``"hand:left"`` / ``"hand:right"``, and nothing else
can complete it (`accepts`). The MIDI adapter completes a desk learn with
the message it received (midi.py, ``MidiIO._learned`` → `learn_control`
→ an ``abs`` / ``rel`` / ``toggle`` MIDI row); the hands adapter a hand
learn with the axis *of that hand* that moved furthest (hands/core.py,
``HandsIO._learn`` → ``learn_source`` → a route: a ``push`` about the
param's base at the session's learn depth wherever the axis or the
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

A learn writes into the **loaded preset** (plan 13 §3.3, D5): the row
goes into the live table — a knob's as a preset-layer desk row, a hand's
as a route — and no file is written. The preset's dirty dot (preset.py,
`Presets.signature` over the table) shows it until a save (⇧F, the preset
strip's save / as…); loading the preset again throws it away. A desk learn
on an invariant control or with the global layer up is refused
(`learn_control` calls `refuse`): the reason is `last`, `refused` is set,
nothing changes, and the learn **stays armed** (plan 17 fork 6) — the
next control that can take it does.

**Unbind** is here too (plan 17 WP1): `unbind` removes what is bound to a
param in the loaded preset — its preset-layer desk rows and its routes,
one kind or both — as one undo step, whether or not a MIDI adapter
exists. `bound` is the same question without the edit (the menu asks it
to know what to list and whether to offer the item at all). A session row
(invariant or global layer) is never removed (D5, D6).

**Learn sink ▸ <role>:<channel>** (plan 27 B3) routes a param *out*: the
menu lists the rig's sink ports (`sinks`, the device registry's
`sink_ports`) and a pick lands at once (`learn_sink`) — there is nothing to
wait for — as a sink row, ``param:<id> → <role>:<channel>`` (routing.py,
`SINK_OP`), in the **session** (`bindings.json`, written now: sinks are
rig, D1 / D9), like a pad learn: no undo step, no preset dirt. It replaces
whatever that port sent before (one source per sink port) and never asks
Replace / Keep: a sink row is not a performer.

**Click a control, then a param** (plan 17 WP4) is the same road taken
from the other end: `pick` holds a desk control (`control`, the on-screen
desk's click), and `map_picked(pid)` is `arm(pid, "desk")` then
`learn_control(control)` — so the op, the feedback, the refusals (D5, D6),
the undo step and the message are the knob learn's. A pick and an armed
learn never stand together: arming lets the pick go, picking cancels the
learn. Which params the on-screen desk offers a pick first is `ranked`
(plan 24 C3), a pure function over the preset's values, its group
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
in the table doing nothing. The MIDI path binds the alias on purpose —
a knob on "the selected band's threshold" should follow the selection —
so that resolution is this object's, not the table's. The rule itself is
the registry's (``Registry.real``, installed by ``build_registry``), the
same one the panel's widgets read through; a registry without it (a
bare test rig) learns the alias as armed.

Imports nothing from the adapters or the panel: the registry and the
table are all it needs.
"""

from __future__ import annotations

from . import modifiers, undo
from .params import PERFORMANCE_GROUPS, Kind, Param, Registry
from .routing import (
    MOD_OPS,
    SAVE_PARAM,
    SINK_OP,
    Binding,
    Bindings,
    Owned,
    base_scheme,
    parse_sink,
)

# plan 24 C1: the desk's SAVE is held, never latched — a learned toggle or
# button row would leave it on, and every bank pad's tap would then save
SAVE_REFUSAL = ("Save is the desk's SAVE (track 8's clip stop, held) — it takes no "
                "learned control")

# what an armed learn may wait for (`Learn.want`, `Learn.wants`) is the
# device registry's to say (plan 27 B2: each device's `wants` — "desk" for
# every MIDI role, "hand:left" / "hand:right" for the hands, "pad" for the
# gamepad, a new device's role for it), and "desk" always: a click on the
# on-screen desk completes a desk learn with no device at all. A Learn the
# registry has not been handed (a bare test rig, the probe) offers what
# today's rig offers
DESK = "desk"
BARE_WANTS = (DESK, "hand:left", "hand:right", "pad")
PAD_SCHEMES = ("pad", "hat", "axis")    # what can complete a "pad" learn

# a push learn's depth when the adapter names none (plan 18 WP3). The hands
# adapter passes its own `hands.learn_depth`, whose default is this number
# written a second time: hands/core.py imports nothing from the package
# (tests/test_learn.py::test_the_two_default_depths_agree holds them equal)
PUSH_DEPTH = 0.25


def centred_target(p: Param) -> bool:
    """A continuous range centred on zero, by declaration: no taper, not
    log, lo == -hi (rot.rate.*, rot.phase.*, camera.yaw / pitch / pan.*,
    dream.hue, any effect uniform declared that way). Nothing here reads
    the param's id or group."""
    return (p.kind is Kind.CONTINUOUS and p.taper is None and not p.log
            and p.hi > 0 and p.lo == -p.hi)


def blocked(table: Bindings, source: str) -> str | None:
    """Why no desk row can be learned onto the control `source` names, as
    the table stands: ``"invariant"`` — the session's on both layers (D6)
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


# ---- what a preset can show, and what it uses (plan 24 C3) ----
#
# A desk control on a param the preset cannot show is "dead": it moves a
# value nobody sees. `cannot_show` is the one rule, by group, read off the
# preset's own bases (the values a load lands, not this frame's modulation):
#
#   pattern.*, view.pattern, view.pattern_mix   the faces are off (view.faces)
#   view.bmp_*                                   the faces are off, or no bitmap file
#   view.points_alpha / view.lines_alpha         points / lines off
#   view.screen_strokes                          points and lines both off
#   fx.mix                                       the effects are off (fx.on)
#   fx.<effect>.<key> (not .on)                  fx.on off, or that effect off
#   dream.* (not dream.on)                       the look-back is off (dream.on)
#   rot.rate.*, view.plane.*                     rotation is off (view.rotate)
#
# Anything else can always show. tools/desk_coverage.py counts with it, and
# click-to-map (`ranked`) never offers a dead param among a preset's own.

_PATTERN = ("view.pattern", "view.pattern_mix")
_BITMAP = ("view.bmp_alpha", "view.bmp_scale", "view.bmp_mode", "view.bmp_amp",
           "view.bmp_rate")
_ROTATE = ("rot.rate.", "view.plane.")


def cannot_show(pid: str, values) -> str | None:
    """Why the preset whose bases are `values` ({id: base}; `.get` is all
    that is asked) cannot show `pid`, in a few words ("faces off",
    "kaleido off"), or None when it can — the rule above. A switch the
    values do not name counts as on."""
    def off(sw: str) -> bool:
        v = values.get(sw)
        return v is not None and not bool(v)
    if pid.startswith("pattern.") or pid in _PATTERN:
        return "faces off" if off("view.faces") else None
    if pid in _BITMAP:
        if off("view.faces"):
            return "faces off"
        f = values.get("view.bmp_file")
        return "no bitmap file" if f is not None and not str(f) else None
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
    if pid.startswith("dream.") and pid != "dream.on":
        return "look-back off" if off("dream.on") else None
    if pid.startswith(_ROTATE):
        return "rotation off" if off("view.rotate") else None
    return None


def _moved(v, d) -> bool:
    """Is a base `v` off its group default `d`? Numbers within a hair are the same."""
    if isinstance(v, bool) or isinstance(d, bool) or not isinstance(v, (int, float)) \
            or not isinstance(d, (int, float)):
        return v != d
    return abs(float(v) - float(d)) > 1e-9 * max(1.0, abs(float(d)))


# the "uses" tiers, best first: what `ranked` says of each of a preset's params
ROUTED, MOVED, ON, DESKED = "routed", "moved", "on", "on the desk"


def ranked(params: list[tuple[str, str]], values, defaults, routed, on_desk,
           shows=None) -> tuple[list[tuple[str, str]], list[tuple[str, list[str]]]]:
    """Click-to-map's offer (plan 24 C3): the params this preset uses,
    ranked, then the rest by group. A pure function.

    `params`: (id, group) of every param a desk control may take, in
    registry order. `values`: {id: base} as loaded. `defaults`: {id: its
    group default} for the preset's own params (the performance groups —
    what a load fills an id the file does not name with). `routed`: the
    ids a route or a macro subscriber drives. `on_desk`: the ids a
    preset-layer row already holds. `shows(pid)`: why it cannot show, or
    None (`cannot_show` over `values` when not given).

    Returns (used, rest). `used` is [(id, why)], in tiers — ``routed`` (a
    route or a macro moves it), ``moved`` (its base is off the group
    default), ``on`` (an effect, the look-back, the faces, the points or
    the lines it belongs to are on, by `cannot_show`'s groups), and last
    ``on the desk`` (already on a control: a second one is seldom what is
    meant) — each tier in registry order. A param the preset cannot show is
    never used. `rest` is every other param as [(group, [id, …])], the
    performance groups first, then the session's, each in registry order."""
    why_not = shows if shows is not None else (lambda pid: cannot_show(pid, values))
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
            elif _switched_on(pid, values):
                tier = ON
        if tier is None:
            rest.setdefault(group, []).append(pid)
        else:
            tiers[tier].append(pid)
    used = [(pid, why) for why, ids in tiers.items() for pid in ids]
    order = {g: i for i, g in enumerate(PERFORMANCE_GROUPS)}
    groups = sorted(rest, key=lambda g: (order.get(g, len(order)), list(rest).index(g)))
    return used, [(g, rest[g]) for g in groups]


def _switched_on(pid: str, values) -> bool:
    """Is `pid` part of a module `cannot_show` knows that is on — its
    switch named in `values` and set? (A param of no such module: False.)"""
    if pid.startswith("pattern.") or pid in _PATTERN or pid in _BITMAP:
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
    if pid.startswith("dream.") and pid != "dream.on":
        return bool(values.get("dream.on"))
    return False


def row_for(source: str, p: Param, when: str | None = None, *,
            centred: bool = False, depth: float | None = None) -> Binding:
    """The row a hand learn makes (plan 18 WP3): its op and depth.

        the target                       a centred axis   a one-sided axis
        continuous, centred on zero      push, depth D    push, depth D
        any other continuous param       push, depth D    position, depth 1
        an enum, a toggle, a trigger,
        a whole-number param             position, 1      position, 1

    D is `depth`, or `PUSH_DEPTH` when the caller named none. A push
    carries no `rest` of its own, so it is centred where the axis
    rests, resolved every frame (`Router.rest_of`): a level hand, or
    a height at the bottom, adds nothing and the preset's value shows
    until the hand moves. A discrete target keeps the fader because a
    push of D about a toggle's base never crosses `params.MOD_ON`, and
    about a whole-number param with a short throw (`dream.steps`, 1–3)
    never reaches the next step: the learn would land and do nothing.
    Nothing reads the target's id or group and nothing is refused: a
    rate-type param lands by the same table as any other."""
    stepped = p.kind is not Kind.CONTINUOUS or p.integer
    if not stepped and (centred or centred_target(p)):
        d = PUSH_DEPTH if depth is None else float(depth)
        return Binding(source, p.id, "push", d, when=when)
    return Binding(source, p.id, "position", 1.0, when=when)


class Learn:
    """The armed param and the question the referee left for the panel."""

    def __init__(self, reg: Registry, table: Bindings, lane=None, devices=None):
        self.reg = reg
        self.table = table
        # the device registry (devices.DeviceRegistry, plan 27 B2), asked
        # what can be armed (`wants`); None: today's rig (BARE_WANTS)
        self.devices = devices
        # the router's `lane` (source → (scheme, index)), so one hand axis
        # named two ways — `hand:7` in an older preset, `hand:right.y` from
        # a learn — is one axis here too (decision register row 20); None:
        # sources compare as strings
        self.lane = lane
        self.learning: str | None = None
        self.want: str | None = None   # what may complete `learning` (`wants`); None: anything
        self.control: str | None = None    # the picked desk control's source; None: none
        self.pending: tuple[Binding, Binding] | None = None
        self.last = ""          # what the last learn did, for the status lines
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
        self.armed_n = getattr(self, "armed_n", 0) + 1

    def take(self) -> str | None:
        """The armed id, cleared — an adapter about to complete the learn
        calls this first so nothing else can complete it too."""
        pid, self.learning = self.learning, None
        self.want = None
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
        want = getattr(self, "want", None)       # a Learn from before a hot reload: None
        if want is None:
            return True
        if source.partition(":")[0] == modifiers.SCHEME:
            return want == modifiers.SCHEME
        if want == DESK:
            return Binding(source, "").is_midi
        if want == "pad":                    # any pad's: ``pad@p2:A`` too (plan 27 B6)
            return base_scheme(source.partition(":")[0]) in PAD_SCHEMES
        if ":" not in want:
            # a role: a source under that scheme (an OSC role's), or one
            # qualified with it (``pad@p2:A`` completes "p2", plan 27 B6)
            return (source.partition(":")[0] == want
                    or Binding(source, "").device == want)
        return source.startswith(f"{want}.")

    # ---- a desk control completes it ----

    def learn_control(self, source: str, profile=None) -> bool:
        """A desk control completes the armed learn: a preset-layer row
        into the loaded preset (plan 13 §3.3). True when it landed.

        The one road onto the desk (plan 17 WP2): the MIDI adapter calls
        it with the message it received, the on-screen desk with the
        control clicked — so it needs no adapter. `profile` is the device's
        module, duck-typed (`is_relative`, `feedback_for`, `named`), for
        the op, the feedback and the control's name; None gives a plain
        `abs` row named by `Binding.describe`.

        It binds the param as armed — a ``band.sel.*`` alias included, on
        purpose: a knob on "the selected band's threshold" should follow
        the selection. Refused, with the reason in `last`, nothing changed
        and **the learn still armed**, on an invariant control (D6) and
        while the global layer is up (D5): both are the session's.
        Otherwise the row replaces every preset-layer row on the control
        (an any-channel row on it included, `Binding.overlaps`) and the
        param's previous preset-layer row in the same role
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
            self.refuse(f"{named(b)} is invariant (the session's) — not learned")
            return False
        if why == "global":
            self.refuse(f"{named(b)} is on the global layer (the session's) "
                        "— latch SHIFT off to learn into the preset")
            return False
        kind, number = b.kind, b.number
        if kind == "cc":
            if profile is not None and profile.is_relative(number):
                b.op = "rel"
            elif p.kind is Kind.TRIGGER:
                b.op = "toggle"
        elif kind == "note":
            b.op = "toggle"
        fb = profile.feedback_for(kind, b.channel, number) if profile is not None else None
        if fb:
            b.feedback, b.ring = fb["feedback"], fb.get("ring", b.ring)
            b.on, b.off = fb.get("on", b.on), fb.get("off", b.off)
        self.take()
        undo.push(f"learn {pid}")                    # one undo step (undo.py, plan 15)
        gone = table.bind(b, write=False)            # the preset rows it replaced
        table.redraw_serial = getattr(table, "redraw_serial", 0) + 1
        glyph = getattr(profile, "glyph", None)
        let_go = list(dict.fromkeys(
            (glyph(x.bare) if glyph is not None else None) or named(x)
            for x in gone if not x.overlaps(b)))
        self.said(f"learned {pid} ← {named(b)} (into the preset)"
                  + (f"; {', '.join(let_go)} let go" if let_go else ""))
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
        """A gamepad button or D-pad direction (``pad:A``, ``hat:UP``)
        completes the armed learn: a button row like a desk note's — a
        trigger fires, a toggle or an enum toggles (the enum steps to its
        next choice), and a fader steps one detent: down for the D-pad's
        DOWN and LEFT, up for anything else (the factory's D-pad rows on
        brightness and speed, one detent at a time; their size is edited
        in the file). True when it landed.

        Pad rows are the session's, as the factory's are (`padmap`): the
        row goes into `bindings.json`, which is written now, and is no undo
        step — nor in any preset. It replaces every row on that button; the
        param's other controls stay."""
        if not self.accepts(source):
            return False
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
            down = Binding(source, pid).bare in ("hat:DOWN", "hat:LEFT")   # any pad's
            op, value = "step", (-1.0 if down else 1.0)
        else:
            op, value = "toggle", 0.0
        self.take()
        table = self.table
        b = Binding(source, pid, op, value)
        gone = [x for x in table.bindings if x.source == source]
        for x in gone:
            table.remove(x)
        table.add(b)
        table.write()
        let_go = ", ".join(dict.fromkeys(x.target for x in gone if x.target != pid))
        self.said(f"learned {pid} ← {b.describe()} (into {getattr(table.path, 'name', 'the session')})"
                  + (f"; {let_go} let go" if let_go else ""))
        return True

    # ---- a sink port takes it (plan 27 B3) ----

    def sinks(self) -> tuple:
        """The rig's sink ports (devices.Port: `address` ``<role>:<channel>``,
        `label`), in list order — what "Learn sink ▸" offers; none without
        a device registry."""
        devs = getattr(self, "devices", None)
        ports = getattr(devs, "sink_ports", None)
        return tuple(ports()) if ports is not None else ()

    def learn_sink(self, pid: str, port: str) -> Binding | None:
        """Send `pid` out on the sink port `port` (``bridge:3``): a sink row
        ``param:<pid> → <port>`` into the session's table, written to
        `bindings.json` now — sinks are rig (D1 / D9), so no undo step and
        no preset dirt, like a pad learn. The row takes the port from
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
        self.said(f"sent {pid} → {port} (into {getattr(table.path, 'name', 'the session')})"
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
        (the row's op and depth, a preset's or one tuned on ROUTING,
        stay). If the param already has a
        different performer the learn is held in `pending` for the panel's
        prompt (`resolve_pending`) — the table untouched until it answers —
        rather than taking the target or being lost. `learning` is cleared
        first, so the hands adapter, which keys off it, cannot fire again.

        A target that is not modulatable (`Param.modulatable`: a rig or
        show setting such as ``ghost.mirror``) is refused with a line the
        performer can read in `last`, the table untouched: the panel never
        offers Learn hand there, and this is the door's own check.
        """
        if not self.accepts(source):     # nothing armed, or armed for something else
            return
        pid = self.take()
        if pid is None:
            return
        p = self.target_for(pid)
        if p is None:
            return
        if not p.modulatable:
            # a setting no performer may drive (ghost.mirror, a rig switch):
            # a route on it would sit dormant, so none is made. The learn
            # is over — no hand can ever complete it — and nothing changed
            if Binding(source, p.id).scheme == "axis":     # any pad's stick (plan 27 B6)
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
            self.said(f"learned {p.id} ← {cur.describe()} (into the preset)")
            return
        if cur is not None:
            self.pending = (b, cur)
            self.said(f"{Owned(cur, b)} — replace?")
            return
        self._place(b)

    def _row(self, source: str, p: Param, when: str | None, *,
             centred: bool = False, depth: float | None = None) -> Binding:
        """The row a hand learn makes (`row_for`, the one table — the GRAPH
        page's cable into a `mod` port makes the same row, plan 28 N3)."""
        return row_for(source, p, when, centred=centred, depth=depth)

    def resolve_pending(self, replace: bool) -> Binding | None:
        """The prompt's answer to a held learn: *Replace* swaps the target's
        performer for the learned row (into the loaded preset, no file
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
        loaded preset's: no file is written (plan 13 §3.3). One undo step
        (undo.py): the rows it took out come back with a Ctrl+Z."""
        undo.push(f"learn {b.target}")
        table = self.table
        gone = [x for x in table.of(b.scheme)
                if x.op in MOD_OPS and self.same_source(x.source, b.source)]
        for x in gone:
            table.remove(x)
        table.replace_owner(b)
        frm = ", ".join(dict.fromkeys(x.target for x in gone if x.target != b.target))
        self.said(f"learned {b.target} ← {b.describe()} (into the preset"
                  + (f"; moved from {frm})" if frm else ")"))

    # ---- unbind ----

    def bound(self, ids) -> tuple[list[Binding], list[Binding], list[Binding]]:
        """What is bound to a param: (the loaded preset's desk rows, its
        routes, the session's MIDI rows). `ids` as for `unbind`. The first
        two are what `unbind` may remove; the third it never does."""
        return bound(self.table, ids)

    def unbind(self, ids, *, desk: bool = True, routes: bool = True, name=None) -> list[Binding]:
        """Remove what is bound to a param, in the loaded preset: its
        preset-layer desk rows (`desk`) and its routes (`routes`). `ids` is
        the drawn param's id and the real one's (an alias and its band; one
        id when they are the same). Returns the rows removed.

        A desk row goes through `Bindings.unbind` (it bumps
        `redraw_serial`: an adapter redraws and the control goes dark, D8);
        a route — any scheme, enabled or not — through `Bindings.remove`,
        its depth subscribers with it. No file is written: the edit is the
        loaded preset's (plan 13 §3.3). One undo step, pushed once and only
        when something goes. `name(b)` gives each row's words for the
        message; without it, `Binding.describe()`. A session row is never
        removed: with nothing else to remove, that is a refusal."""
        ids = _ids(ids)
        if not ids:
            return []
        real = ids[-1]
        name = name if name is not None else Binding.describe
        mine, routed, session = self.bound(ids)
        gone = (mine if desk else []) + (routed if routes else [])
        if not gone:
            if desk and session:
                b = session[0]
                where = "on the global layer" if b.layer == "global" else "invariant"
                self.refuse(f"{name(b)} → {b.target} is {where} (the session's, "
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
    the session's, listed by the param's menu, never removed by Unbind."""
    ids = _ids(ids)
    return [b for b in table.bindings
            if b.is_sink and b.source.partition(":")[2] in ids and b.scheme == "param"]


def _ids(ids) -> tuple[str, ...]:
    """One id or several, as a tuple with no repeats, in order."""
    return (ids,) if isinstance(ids, str) else tuple(dict.fromkeys(ids))


def bound(table: Bindings, ids) -> tuple[list[Binding], list[Binding], list[Binding]]:
    """`Learn.bound` over any table (the panel's menu lists from it with
    or without a learn object, so its lines are what Unbind removes):
    (preset-layer desk rows, routes, the session's MIDI rows) on `ids`. A
    route is a performer row from a continuous source — never a MIDI row,
    whatever its op, so a session row can not come back as a "route"."""
    ids = _ids(ids)
    midi = [b for b in table.bindings if b.is_midi and b.target in ids]
    routes: list[Binding] = []
    for pid in ids:
        routes += [b for b in table.routes_to(pid)
                   if not b.is_midi and not any(b is x for x in routes)]
    return ([b for b in midi if b.layer == "preset"], routes,
            [b for b in midi if b.layer != "preset"])
