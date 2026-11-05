"""The deck: one look's objects, built in one order (plan 44 D1).

A `Deck` bundles what plan 44 §2 marks "per deck", as the objects exist
today: the registry (`reg`), the view state (`view`), the binding table
(`table`), the router and the sources it reads (`sources`, plan 44
D2), the three modulator banks (`lfos`, `envs`,
`seq`), the presets and their graph section (`presets`, `presets.graph`),
the learn, the undo and the marks it restores through, and — in the app,
never headless — the renderer and the hold, and the clock the banks step on. D1 changes no behaviour:
there is one deck, `app.main` builds it, and `app.Host` and `ui.Panel`
keep their flat handles, assigned from it.

`Deck.build` holds the lines of `app.main` from the view state to
`undo.install` in their order, which is the registry's order (what
`library.attach` calls "default") and the attach order. Where `main`
builds a rig object between two deck lines — the hands' setup, the
outputs' params, the panel, the devices — `build` calls the caller's hook
at that very place (the rig's own wiring that declares no param, such as
the library's band hooks, stays with the caller, before `build`), so the headless rig (`tests/test_undo.boot`) and the
app run the same lines and cannot drift apart. A hook the caller leaves
out is a step that rig does not have.

`Deck.targets()` is the deck itself and then the hot-reload tuples `main`
listed for these objects, in the order it listed them; `main` hands the
reloader the deck's and then the rig's. A save of this file re-classes
the live deck, and a field added to `Deck` with a default is back-filled
on it (`hotreload._backfill_dataclass`); but `build` does not re-run, so
what a new field should hold on a running deck arrives only with a
restart, and a PR that adds one says "restart" (plan 44 §8).

Plan 44 D4 adds the second deck and the fade. `Deck.beside` builds a deck
beside the first over the same session, sources and clock, with a renderer on
the same context; nothing points at it — no controller, no page, no undo —
and it writes no file. `Mix` holds `output.xfade` (`register_xfade`) and
`Fade` runs it: at 0 nothing of deck 2 is drawn; above 0 deck 2's renderer
draws every output into a frame texture at that output's size, which the
on-air deck's pass mixes in before the dim (`Renderer.mix_pass`), and the one
dream worker is lent to it. A raise in deck 2's draw leaves the on-air deck's
picture alone and is said on `Fade.error`.

Plan 44 D5a adds `MetaController`, what owns the two decks and every holder's
pointer (`pointer.Pointer`). Every pointer starts on deck 1 and nothing in the
app moves one yet. D5b splits undo: a stack per deck, scoped to its preset
(`in_preset`), and one for the meta controller (`meta_stack`), so three.
Plan 55 adds the players (`players.Players`): a controller's pointer goes where
its player's duty says.

D5c makes it a DJ mixer's crossfader, with no swap: `output.xfade` 0 is deck 1
alone, 1 deck 2 alone, and on air is whichever the fader is closer to
(`MetaController.follow_fader`, `MIDDLE`). `Fade` mixes the other deck over the
one on air by `Fade.k`, the other's share. Two verbs: the crossfade, by hand or
timed (`crossfade`, `tick`), and `copy_on_air`. Nothing in `app.main` calls them
yet, so deck 1 stays on air and raising the fader mixes as D4 did; D5d wires them.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from typing import Any

from . import envelope, geometry, lfo, poi, sequencer, tempo, totem
from . import undo as undos
from .fx import FxState
from .ghost import GhostState
from .hold import Hold, preview_renderer
from .hold import register as register_hold
from .learn import Learn
from .library import Marks, MetaMarks
from .lookback import DreamState
from .outputs import Offscreen, View, preview_size
from .params import Registry, SessionRegistry, build_registry, part_of
from .players import Duty, Players
from .pointer import Pointer
from .preset import Presets
from .routing import Bindings, Router, Sources
from .view import ViewState


def in_preset(p) -> bool:
    """Is `p` a param of the preset, what a `Deck`'s undo stack watches (plan 44
    D5b)? A meta param is on the meta controller's stack (`meta_stack`)."""
    return part_of(p) == "performance"


@dataclass
class RigMade:
    """What the caller's hooks returned, as `Deck.build` called them: the
    rig's objects built between the deck's lines (the hands' setup, the
    outputs, the panel, the devices). `build` threads each to the hooks
    after it that take it, and fills this record when the caller hands
    one in (`made=`), so the caller keeps them without shared state."""

    hands: Any = None
    outputs: Any = None
    panel: Any = None
    devices: Any = None


@dataclass
class Deck:
    """One look and its controls (plan 44 §1), today's singletons bundled.
    `renderer` and `hold` are None on a headless deck (no GL)."""

    reg: Registry
    view: ViewState
    table: Bindings
    router: Router
    lfos: lfo.LFOs
    envs: envelope.Envelopes
    seq: sequencer.Sequencer
    # the tap-tempo clock the banks step on. Built here today, in main's
    # order; plan 44 §2 calls it shared — D3+ passes the rig's one in
    # (`build(clock=…)`) rather than building one per deck
    clock: tempo.Clock
    presets: Presets
    learn: Learn
    undo: undos.Undo
    marks: Marks
    renderer: Any = None
    hold: Hold | None = None
    # what the sources said this frame (routing_sources.Sources, plan 44
    # D2): the router's shared half, the one the devices and the analyzer
    # feed. Built here while there is one deck (`build(sources=…)` hands a
    # rig's one in, so two routers read one feed); plan 44 §2 calls it shared
    sources: Sources | None = None
    # the bands' names in strip order (`undo.Undo.tag`): the shape the meta
    # controller's stack keeps `band.*` values for (`meta_stack`)
    band_shape: Callable[[], Any] | None = None

    @property
    def graph(self):
        """The presets' graph section (`preset.GraphSection`)."""
        return self.presets.graph

    @property
    def session(self) -> SessionRegistry | None:
        """The rig's params this deck's registry holds by reference (plan 44
        D3, `params.SessionRegistry`): one for every deck."""
        return self.reg.session

    @property
    def session_table(self):
        """The rig's half of the binding table this deck's table holds by
        reference (plan 44 D3, `routing.SessionTable`): the session rows
        and `bindings.json`."""
        return self.table.session

    @classmethod
    def build(cls, *, library, control, audio, table: Callable[[Registry], Bindings],
              renderer=None, media=None, restart: Callable[[], Any] | None = None,
              dream=None, fx=None, ghost=None,
              clock: tempo.Clock | None = None, lfos: lfo.LFOs | None = None,
              sources: Sources | None = None,
              session: SessionRegistry | None = None,
              hands: Callable[[Registry], Any] | None = None,
              outputs: Callable[[Registry], Any] | None = None,
              panel: Callable[..., Any] | None = None,
              devices: Callable[..., Any] | None = None,
              made: RigMade | None = None,
              attach: bool = True, startup: bool = True, install: bool = True,
              on_air: bool = True, tag: Callable[[], Any] | None = None,
              warm: bool = False) -> Deck:
        """`app.main`'s deck lines, in their order. `library`, `control`
        and `audio` (anything with a `.chain`) are the rig's, built and
        wired to each other first (the band hooks, `control.library`);
        `table(reg)` loads the binding table and declares the desk's
        params on `reg`. `renderer` (the app's; None headless) supplies the
        look-back's, the effects' and the hands' states and gets a hold;
        headless, `dream` / `fx` / `ghost` stand in for them (a fresh one
        each when None) — given with a renderer they are a ValueError,
        since the renderer's states are the ones it draws. `media` is the channels' `MediaState`, `restart`
        the `app.restart` param's callback, `clock` / `lfos` a clock and
        an LFO bank to use in place of new ones, `sources` the shared
        sources the router reads (plan 44 D2; new ones when None) — their
        clock, when they have one, is the deck's unless `clock` is given,
        and a different `clock` is refused there. `session` (plan 44 D3) is
        the rig's params (`params.build_session`) this deck's registry
        follows; None: `build_registry` makes them (the one deck there is
        today). The hooks, each called
        where `main` builds that rig object, each returning what it made:
        `hands(reg)` the hands' setup, `outputs(reg)` the outputs' params
        and switches, `panel(reg, view, clock=, lfos=, envs=, seq=, hold=,
        output=)` the panel (its `ui.*` params, and its handles on what
        exists by then; `output` is what `outputs` returned), and
        `devices(reg, router, learn, panel=, hand_settings=)` the devices —
        before the startup preset lands (`panel` and `hand_settings` are
        what those hooks returned). A hook left out passes None on; `made`
        (a `RigMade`) collects every hook's return for the caller.

        Three steps act on what there is one of in the process, and are
        switches so a second deck can leave them alone: `attach` (the
        library binds this registry, "default" is its state now),
        `startup` (the show's startup preset lands on this deck) and
        `install` (this deck's undo is the one `undo.push` and the
        `edit.*` triggers reach). All three default on, as `main` has them;
        a second deck built beside the first passes all three False, and
        D2+ decides their real shape. `on_air` (plan 44 D3, review of #351):
        this deck is the session's lead — its `apply` lands the session's
        params once a frame; a deck built beside it passes False. `warm`: build every shape's geometry
        on a background thread once the startup preset has landed."""
        if renderer is not None:
            given = [k for k, v in (("dream", dream), ("fx", fx), ("ghost", ghost))
                     if v is not None]
            if given:
                raise ValueError(f"Deck.build: {', '.join(given)} given with a renderer, "
                                 "whose own states the deck's params must drive")
            dream, fx, ghost = renderer.lookback.state, renderer.fx.state, renderer.ghost.state
        # one clock for every deck (plan 44 §2): a clock other than the shared
        # sources' is refused before anything registers on it
        if (sources is not None and clock is not None and sources.clock is not None
                and clock is not sources.clock):
            raise ValueError("Deck.build: the sources step every bank on their own clock; "
                             "a different `clock` was given")
        library = library.base           # (a deck's own view, `Deck.beside`: the one library)
        on_deck = library.on_deck()      # this deck's bank and presets (plan 44 D5a)
        s = ViewState()
        reg = build_registry(s, control, audio, on_deck.project,
                             dream=dream if dream is not None else DreamState(),
                             fx=fx if fx is not None else FxState(),
                             ghost=ghost if ghost is not None else GhostState(),
                             media=media, restart=restart, session=session)
        beside = session is not None and not on_air    # a deck beside the first (`beside`)
        if on_air and reg.session is not None:
            # (review of #351: the deck on air lands the session's params —
            # named, never "whichever registry followed first")
            reg.session.lead = reg
        made = made if made is not None else RigMade()
        if hands is not None:
            made.hands = hands(reg)            # before attach: "default" includes them
        # the tap-tempo clock and the LFO bank (tempo.py, lfo.py; four by
        # default, up to 16, plan 31 B): their knobs are params too, so a
        # preset carries a tempo and an LFO arrangement
        # one clock for every deck (plan 44 §2): shared sources that have
        # one bring it, and the router refuses any other (`Router.use_bank`)
        if clock is None and sources is not None:
            clock = sources.clock
        clock = clock if clock is not None else tempo.Clock()
        lfos = lfos if lfos is not None else lfo.LFOs()
        if not beside:                         # the session's, declared by the first deck
            tempo.register(reg, clock)
        lfo.register(reg, lfos, clock)
        # plan 31: the envelope bank (the five lane envelopes, plus extras) and
        # the step sequencer that fires them — registered beside the LFOs and
        # before attach, so "default" holds their knobs and an empty pattern
        envs = envelope.Envelopes()
        seq = sequencer.Sequencer()
        envelope.register(reg, envs, clock)
        sequencer.register(reg, seq, clock)
        # the render window's placement registers before attach, so "default"
        # includes output.* and reset / the dirty dot see them (audit L6)
        if outputs is not None:
            made.outputs = outputs(reg)
        # plan 38: the projector held while the next look is built — rig
        # controls beside the switches; its undo is handed over once it exists
        hold = None
        if renderer is not None and not beside:
            hold = Hold(reg, renderer, make=lambda: preview_renderer(renderer))
            register_hold(reg, hold, now=time.perf_counter)
        # one binding table for keys, pad, MIDI and lanes — read before
        # attach for the same reason: the desk's session param, `desk.slew`,
        # is the table's
        bindings = table(reg)
        if attach:
            library.attach(reg)
        if panel is not None:
            # the panel's own ui.* params, and its handles on what exists now
            made.panel = panel(reg, s, clock=clock, lfos=lfos, envs=envs, seq=seq, hold=hold,
                               output=made.outputs)
        # the router: this deck's evaluator over the sources every source
        # feeds (plan 44 D2) — the rig's when handed in, else its own
        sources = sources if sources is not None else Sources()
        router = Router(reg, bindings, sources=sources)
        router.use_lfos(lfos, clock)           # they step inside the pass (plan 28 N0)
        router.use_bank(envs, clock)           # …and so do the envelopes (plan 31)
        router.use_sequencer(seq, envs)        # after the banks begin, before the plan
        # the presets (preset.py): the library's `presets/` files, landed on the
        # registry and the table; the project's bank loads through it
        presets = Presets(on_deck, reg, router)
        if renderer is not None:
            # plan 26 A4: a preset's graph section sets the renderer's wiring and
            # hands an extra hands node its own state (`Renderer.ghost_states`)
            presets.graph.attach(renderer)
            # plan 44 D3: the bus cuts are the loaded preset's — the renderer
            # reads them off the presets (`graph.rig_of`: `Presets.rig`)
            renderer.rig_source = presets
            renderer.deck_reg = reg            # whose picture it is (the poi's guide)
        if hold is not None:
            hold.section = presets.graph       # plan 38 B3: landings keep the held program's nodes
        # one Learn over the live table, whatever the MIDI gate says: a knob
        # or a hand completes it, the panel's prompt settles what the referee
        # refused (learn.py; the band.sel.* rule is the registry's `real`)
        learn = Learn(reg, router.table, lane=router.lane)   # hand:7 and hand:right.y: one axis
        if devices is not None:
            made.devices = devices(reg, router, learn, panel=made.panel,
                                   hand_settings=made.hands)
        # the project's startup preset (D11), once, now that everything it lands
        # on exists; a missing one is said on the panel and the app runs on
        if startup:
            library.project.load_startup()
        if warm:
            # every shape's faces, triangles and UVs built now, off the frame, the
            # startup preset's shape first, so the first switch to a big one
            # (rectified 600-cell, 600-cell, 120-cell, Clifford torus) does not stutter
            geometry.warm_all(first=s.shape)
        # undo (undo.py, plan 15 WP1), built after the startup preset so a
        # launch starts with an empty stack: this deck's preset only (plan 44
        # D5b), bases through the registry, table parts through the table, what
        # is loaded through the deck's marks, and a restore tells the router its
        # macros are acted on. The meta params are on `meta_stack`'s
        marks = Marks(presets.lib)
        undo_obj = undos.Undo(reg, router.table, marks=marks, only=in_preset,
                              on_restore=router.sync_macros,
                              # the LFOs' membership (plan 31 B), read off the
                              # router at each step, so a re-classed router counts
                              banks=lambda: router._banks())
        reg.chase_undo = undo_obj          # one base chase hold, one step here (plan 52)
        if install:
            undos.install(undo_obj)        # what undo.push and the edit.* triggers reach
        if hold is not None:
            hold.undo = undo_obj           # Drop goes back to the hold's point through it
        return cls(reg=reg, view=s, table=router.table, router=router, lfos=lfos, envs=envs,
                   seq=seq, clock=clock, presets=presets, learn=learn, undo=undo_obj, marks=marks,
                   renderer=renderer, hold=hold, sources=sources,
                   band_shape=tag if tag is not None else (
                       (lambda: tuple(s.name for s in audio.chain.spec))
                       if audio is not None else None))

    def chase(self, on: bool) -> bool:
        """Hold or let go of the base chase on this deck (plan 52): the
        performer into this deck's bases, one step on this deck's undo.
        Returns whether it is on now. `deck.chase` is the same road."""
        return self.reg.base_chase(on, steps=self.undo)

    @classmethod
    def beside(cls, first: Deck, *, renderer=None, media=None, lfos=None) -> Deck:
        """A deck beside `first` (plan 44 D4): its own look — registry,
        view, table, router, banks, presets, undo, `renderer` (on the same
        context; None headless) and `media` (its `Channels`, over the rig's
        sources) — over `first`'s session params and rows, sources and clock.
        It attaches to nothing, loads nothing, installs nothing: the library,
        the strip and the undo keys stay `first`'s until `MetaController.point_panel`
        moves them. Nothing points at it yet."""
        return cls.build(
            library=first.presets.lib, control=None, audio=None,
            table=lambda reg: Bindings([], session=first.table.session),
            renderer=renderer, media=media, lfos=lfos,
            session=first.session, sources=first.sources,
            attach=False, startup=False, install=False, on_air=False,
            tag=first.band_shape)

    def targets(self) -> list[tuple[Any, str, str]]:
        """The live objects a hot reload re-classes, as (object, module,
        class) — the deck itself, then the ones `app.main` listed for these
        objects, in its order; re-evaluated each swap, so a voice or a
        preview renderer made since counts. The clock is listed here while
        the deck builds it (plan 44 §2 calls it shared: D3+ hands the rig's
        in, and the rig lists it)."""
        r, hold = self.renderer, self.hold
        return [
            (self, "deck", "Deck"),
            *([(r, "render", "Renderer"),
               (r.scene, "render", "SceneTarget"),
               (r.cover, "render", "CoverTarget"),
               (r.lookback, "lookback", "Lookback"),
               (r.lookback.state, "lookback", "DreamState"),
               (r.fx, "fx", "FxChain"),
               (r.fx.state, "fx", "FxState"),
               (r.ghost, "ghost", "Ghost"),
               (r.ghost.state, "ghost", "GhostState")] if r is not None else []),
            (self.view, "view", "ViewState"),
            (self.reg, "params", "Registry"),
            # plan 44 D3: the rig's params this deck holds by reference (listed
            # here while there is one deck; D4+ hands the rig's in)
            *([(sr, "params", "SessionRegistry")]
              if (sr := getattr(self.reg, "session", None)) is not None else []),
            *[(p, "params", "Param") for p in self.reg],
            (self.marks, "library", "Marks"),
            (self.undo, "undo", "Undo"),
            *([(hold, "hold", "Hold")] if hold is not None else []),   # plan 38
            # …and its preview renderer once made
            *([(hold.preview, "render", "Renderer")]
              if hold is not None and hold.preview is not None else []),
            # the router's shared half (plan 44 D2), while the deck builds it
            # (getattr: a stand-in deck, or one from before D2, has none)
            *([(src, "routing_sources", "Sources")]
              if (src := getattr(self, "sources", None)) is not None else []),
            (self.router, "routing", "Router"),
            (self.presets, "preset", "Presets"),
            # plan 44 D5a: its view of the library (getattr: a stand-in deck has none)
            *([(on, "library", "DeckLibrary"), (on.project, "library", "DeckProject")]
              if (on := getattr(self.presets, "lib", None)) is not None else []),
            (self.presets.graph, "preset", "GraphSection"),      # plan 26 A4
            (self.learn, "learn", "Learn"),
            (self.clock, "tempo", "Clock"),
            (self.lfos, "lfo", "LFOs"),
            # the LFOs as they are at this swap: N of them, with gaps (plan 31 B)
            *[(lf, "lfo", "LFO") for lf in self.lfos.lfos],
            # the envelopes the same way (plan 31: five lane ones and the
            # extras), and the sequencer with its lanes
            (self.envs, "envelope", "Envelopes"),
            *[(e, "envelope", "Envelope") for e in self.envs.voices],
            (self.seq, "sequencer", "Sequencer"),
            *[(ln, "sequencer", "Lane") for ln in self.seq.lanes],
            # the totem's state (plan 47), once the panel hook registered it
            *([(st, "totem", "TotemState")]
              if (st := totem.state_of(self.reg)) is not None else []),
            # …and the poi's (plan 47, the poi)
            *([(sw, "poi", "PoiState")]
              if (sw := poi.state_of(self.reg)) is not None else []),
        ]


# ------------------------------------------------------- the two decks (D5a)

# the holders that are no device; a device's holder name is its role
KEYS = "window:keys"
MOUSE = "window:mouse"


class MetaRows:
    """The meta controller's table as `undo.Undo` reads a table: its rows, and none
    of what a deck's table has of its own (routes, desk layer, macros)."""

    bindings: tuple = ()
    macros: dict = {}  # noqa: RUF012 — never mutated: there are none

    def __init__(self, session):
        self.session = session

    @property
    def rows(self) -> list:
        return self.session.rows

    def set_rows(self, rows) -> None:
        self.session.set_rows(rows)

    def routes(self) -> tuple:
        return ()

    def desk(self) -> tuple:
        return ()

    def macros_doc(self) -> dict:
        return {}


def meta_stack(first: Deck) -> undos.Undo:
    """The meta controller's undo stack (plan 44 D5b): an `Undo` over the
    `SessionRegistry` and the `SessionTable` every deck holds by reference, what
    is loaded through the library's `MetaMarks`. `first` is whichever deck has
    the band hooks; the stack is no deck's."""
    return undos.Undo(first.session, MetaRows(first.session_table),
                      marks=MetaMarks(first.presets.lib.base), tag=first.band_shape)


def _carry(src: Deck, dst: Deck) -> None:
    """What `Presets.document` does not hold and a copy must (the reading's rows 3
    and 4), after the doc road landed the rest: the turn as it stands (`pose` folds
    it, which is not the same bits), the field's and the media path's phases, each
    param's running state with its chase ledger (`Registry.take_running`: the pose's
    ledger too, which no snapshot holds), each row's and bank's, and the renderer's
    clocks. One clock steps both
    banks, so nothing here is a lock: each deck runs on from where the copy left it.
    A clip's place and the trails are not carried: a load's start empty."""
    dst.router.modgraph                  # noqa: B018 — its lost rows forgotten first (plan 52)
    sv, dv = src.view, dst.view
    dv.ang, dv.body, dv.held = list(sv.ang), copy.copy(sv.body), sv.held
    dv.inst_phase, dv.media_phase = sv.inst_phase, sv.media_phase
    dst.reg.take_running(src.reg)
    dst.router.take_running(src.router)
    theirs = src.router._banks()
    for scheme, bank in dst.router._banks().items():
        _carry_bank(theirs[scheme], bank)
    dst.seq.__dict__.update({k: copy.copy(v) for k, v in src.seq.__dict__.items()
                             if k in SEQ_RUNNING})
    if src.renderer is not None and dst.renderer is not None:
        dst.renderer.take_running(src.renderer)


# the sequencer's runtime, what `sequencer.Sequencer` keeps on the class until it runs
SEQ_RUNNING = frozenset(("k_last", "epoch_seen", "playhead", "pulses", "shift", "pending",
                         "last_spb", "was_running", "stopped"))


def _carry_bank(src, dst) -> None:
    """One modulator bank's running state: each voice's fields marked runtime (not
    in its `repr`), the frame's outputs and a random LFO's stream."""
    for n, voice in src._voices.items():
        mine = dst._voices.get(n)
        if mine is None:
            continue
        for f in fields(voice):
            if not f.repr:
                setattr(mine, f.name, copy.deepcopy(getattr(voice, f.name)))
    dst.outputs = list(src.outputs)
    dst.pending = getattr(src, "pending", False)
    rng = getattr(src, "rng", None)
    if rng is not None:
        dst.rng.setstate(rng.getstate())


class MetaController:
    """What is set for a performance or an install, around the looks: it owns
    exactly two `Deck`s (`docs/GLOSSARY.md`) and says which deck each holder is
    on. Each controller has its own pointer (`pointer(role)`, `point`), and so do
    the keys and the mouse, and the panel has its own (`panel_pointer`,
    `point_panel`): none moves with another, so players can sit on either deck
    and the panel can show either. `on_air_pointer` is the deck the outputs
    show; it stays on deck 1 until the crossfader decides it (D5c).

    A holder reads through its pointer each time. `point` moves only the
    pointer: what a holder kept of the deck it left is its own to let go when
    it next looks (`MidiIO._follow_pointer`). A deck not in `decks` is refused.

    `undo` is its own stack (`meta_stack`, plan 44 D5b), beside one on each deck:
    `stacks` are the three, all ticked each frame. A stack stays with its `Deck`
    whatever points at it.

    `players` (plan 55) say where the controllers go: a controller's pointer
    starts on the deck its player's duty says (`deck_for`), `move_player` moves
    all a player holds, `register` moves a controller to a player. On air is
    `on_air`, off air `off_air`; when the crossfader moves `on_air_pointer`
    (`follow_fader`) both duties go across. The keys and the mouse are no player's
    and act on the picture, so they go across too; the panel stays where it was
    put. `on_players` is told when who holds what changes: a pad's rows name its
    player, so the device list reads it again.

    `mix` is the crossfader (`output.xfade`, `output.xfade_s`): `tick` runs a
    timed `crossfade` and follows the fader, and `parked` is the one list of decks
    off air, what `Host.off_air` reads."""

    # (class-level: read by a meta controller from before a hot reload)
    timed: TimedFade | None = None

    def __init__(self, first: Deck, second: Deck, players: Players | None = None,
                 mix: Mix | None = None):
        self.decks = (first, second)
        self.mix = mix if mix is not None else Mix()
        self.parked = [second]
        self.on_air_moved: list[Callable[[Deck], Any]] = []   # told after on air moves
        self.players = players if players is not None else Players()
        self.on_players: list[Callable[[], Any]] = []
        self.seats: dict[str, int] = {}     # role → the player it was last placed for
        self.on_air_pointer = Pointer(first)
        self.panel_pointer = Pointer(first)
        self.pointers: dict[str, Pointer] = {}
        self.on_panel: list[Callable[[Deck], Any]] = []   # told after the panel moves
        self.undo = meta_stack(first)
        undos.install_meta(self.undo)

    @property
    def on_air(self) -> Deck:
        return self.on_air_pointer.deck

    @property
    def off_air(self) -> Deck:
        return self.decks[1] if self.on_air is self.decks[0] else self.decks[0]

    @property
    def panel(self) -> Deck:
        return self.panel_pointer.deck

    @property
    def stacks(self) -> tuple[undos.Undo, ...]:
        """Every undo stack: each deck's and this one's."""
        return (self.decks[0].undo, self.decks[1].undo, self.undo)

    def pointer(self, holder: str) -> Pointer:
        """`holder`'s pointer, on deck 1 the first time it is asked for, and
        kept by name, so a controller unplugged and back is where it was."""
        got = self.pointers.get(holder)
        if got is None:
            if holder in (KEYS, MOUSE):
                deck = self.on_air
            else:
                player = self.players.player_of(holder)
                deck, self.seats[holder] = self.deck_for(player.duty), player.number
            got = self.pointers[holder] = Pointer(deck)
        return got

    def deck_for(self, duty: Duty | str) -> Deck:
        """The `Deck` a duty means now."""
        return self.on_air if Duty(duty) == Duty.ON_AIR else self.off_air

    def deck_of_player(self, number: int) -> Deck:
        return self.deck_for(self.players.get(number).duty)

    def move_player(self, number: int, duty: Duty | str) -> None:
        """Player `number` to `duty`, remembered, and everything it holds with
        it. It stays until someone moves it. Each controller lets go of the deck
        it left at its next `act` (`Router.pad_left`, `MidiIO._follow_pointer`,
        `routing.let_go_lost`); a row on it there goes dormant in that deck's
        next pass."""
        self.players.move(number, duty)
        self._place(number)

    def _place(self, number: int) -> None:
        deck = self.deck_of_player(number)
        for role, p in self.pointers.items():
            if role not in (KEYS, MOUSE) and self.players.player_of(role).number == number:
                p.deck, self.seats[role] = deck, number

    def reseat(self) -> None:
        """A controller whose player changed by a change of the device list (the
        first pad disabled, so the next is player 1's) goes to that player's deck.
        One whose player is the same stays where it is, mapped elsewhere or not."""
        for role, p in self.pointers.items():
            if role not in (KEYS, MOUSE):
                number = self.players.player_of(role).number
                if self.seats.get(role) != number:
                    p.deck, self.seats[role] = self.deck_of_player(number), number

    def place_players(self) -> None:
        """Every player where its duty says: for what moves on air (D5c), so an
        on-air player stays on air and an off-air one with the off-air `Deck`."""
        for player in self.players:
            self._place(player.number)

    def register(self, role: str, number: int) -> None:
        """Player `number` holds the controller `role` from now on, remembered;
        the controller goes to that player's deck."""
        self.players.hold(role, number)
        self.point(role, self.deck_of_player(number))
        self.seats[role] = number
        for fn in self.on_players:
            fn()

    def _ours(self, deck: Deck) -> Deck:
        if not any(deck is d for d in self.decks):
            raise ValueError("MetaController: that deck is not one of its two")
        return deck

    def point(self, holder: str, deck: Deck) -> None:
        """Move one holder to `deck`; nothing else moves."""
        self.pointer(holder).deck = self._ours(deck)

    def point_panel(self, deck: Deck) -> None:
        """Move the panel to `deck`, and with it what follows the panel: the
        library's verbs (`Library.pointer` is this pointer), Learn, and the undo
        that `undo.push` and the `edit.*` triggers reach. Nothing else moves."""
        self.panel_pointer.deck = self._ours(deck)
        undos.install(deck.undo)
        for fn in self.on_panel:
            fn(deck)

    # ---- the crossfader (D5c): on air by the fader's side, no swap ----

    def follow_fader(self) -> bool:
        """On air follows the side the fader is on, past `MIDDLE` so a fader
        sitting at the middle never flaps. True when on air moved."""
        x, first, second = self.mix.xfade, *self.decks
        if self.on_air is first and x >= 0.5 + MIDDLE:
            self._go_on_air(second)
        elif self.on_air is second and x <= 0.5 - MIDDLE:
            self._go_on_air(first)
        else:
            return False
        return True

    def _go_on_air(self, deck: Deck) -> None:
        """`deck` on air: the session's lead with it, what the deck left held of a
        chase let go there (one step on its stack), every player where its duty now
        says, the keys and the mouse with the picture they act on. A press across
        the move ends on the deck it was made on, as any move's does
        (`routing.let_go_lost`). The panel and the undo it reaches stay."""
        left = self.on_air
        left.chase(False)
        self.on_air_pointer.deck = deck
        self.parked[0] = left
        session = deck.session
        if session is not None:
            session.lead = deck.reg
        self.place_players()
        for holder in (KEYS, MOUSE):
            p = self.pointers.get(holder)
            if p is not None:
                p.deck = deck
        for fn in self.on_air_moved:
            fn(deck)

    def crossfade(self, to: float | None = None) -> None:
        """Run the fader to `to` (None: the end of the deck off air) over
        `output.xfade_s` seconds, read now; 0 is a cut. `tick` moves it, from the
        fader's place. A hand on the fader meanwhile ends it there."""
        if to is None:
            to = 1.0 if self.on_air is self.decks[0] else 0.0
        self.timed = TimedFade(self.mix.xfade, float(to), self.mix.seconds)

    def tick(self, now: float, dt: float) -> None:
        """Once a frame: a timed fade's step, through `output.xfade`'s `Param`, then
        on air by the fader. `dt` dates a fade asked for since the last frame."""
        run = self.timed
        if run is not None:
            if self.mix.xfade != run.wrote:
                self.timed = None             # a hand took the fader
            else:
                if run.began is None:
                    run.began = now - dt
                done = now - run.began >= run.seconds
                x = run.to if done else (run.start + (run.to - run.start)
                                         * (now - run.began) / run.seconds)
                self._write_fader(x)
                run.wrote = self.mix.xfade
                if done:
                    self.timed = None
        self.follow_fader()

    def _write_fader(self, x: float) -> None:
        p = self.decks[0].reg.get("output.xfade")
        if p is not None:
            p.set(x)
        else:
            self.mix.xfade = x                # (no param: a rig with no outputs hook)

    # ---- copy on air to off air (D5c): the second verb ----

    def copy_on_air(self) -> list[str]:
        """The deck on air's look onto the deck off air, so the two run as one
        until someone touches either. One step on the off-air deck's stack; onto an
        empty deck, none, since there is nothing to go back to. What it does to the
        deck on air: nothing. Returns the ids the document names that the deck
        lacks. See `_carry` for what a document does not hold."""
        src, dst = self.on_air, self.off_air
        name, presets = src.presets.current, dst.presets
        empty = presets.current is None and dst.graph.spec is None and not dst.undo.stack
        doc = src.presets.document(name or "untitled")
        undos.push_on(dst.reg, f"copy {name or 'untitled'} from on air", load=True)
        missing = presets.load_doc(doc)
        _carry(src, dst)
        presets.landing = (*copy.deepcopy(src.presets.landing[:2]), None)
        presets._landed(name)
        presets.unsaved = src.presets.unsaved
        if empty:
            dst.undo.clear()
        return missing

    def targets(self) -> list[tuple[Any, str, str]]:
        """The live objects a hot reload re-classes (the decks list their own)."""
        return [(self, "deck", "MetaController"),
                (self.players, "players", "Players"),
                *[(p, "players", "Player") for p in self.players],
                (self.undo, "undo", "Undo"),
                (self.undo.marks, "library", "MetaMarks"),
                (self.undo.table, "deck", "MetaRows"),
                (self.on_air_pointer, "pointer", "Pointer"),
                (self.panel_pointer, "pointer", "Pointer"),
                *[(p, "pointer", "Pointer") for p in self.pointers.values()]]


# ------------------------------------------------------------- the fade (D4)

@dataclass
class Mix:
    """What `output.xfade` and `output.xfade_s` write: the crossfader, 0 deck 1
    alone and 1 deck 2 alone, and the seconds a timed fade runs it over
    (`MetaController.crossfade`)."""

    xfade: float = 0.0
    seconds: float = 2.0


@dataclass
class TimedFade:
    """A timed fade running: from `start` to `to` over `seconds`. `began` is set at
    its first `tick`; `wrote` is where it left the fader, so a hand on it shows."""

    start: float
    to: float
    seconds: float
    began: float | None = None
    wrote: float = 0.0

    def __post_init__(self):
        self.wrote = self.start


# How far past the middle the fader must go before on air moves, each way: 4 steps
# of a 7-bit desk fader (1/127), more than one at rest jitters by, and small
# enough that "closer to" is what it reads as
MIDDLE = 0.03

# (the panel's words change with D5d, which is what makes on air move in the app)
XFADE_TIP = ("Mixes the other deck's picture over this one's on every output, before "
             "the dim: 0 this deck alone, 1 the other deck alone. Never saved; nothing "
             "on the desk by default (the crossfader stays the master dim), learn it "
             "onto a fader.")
XFADE_S_TIP = "How long a timed fade runs the crossfader, in seconds. 0 is a cut. Never saved."


def register_xfade(reg, mix: Mix) -> list[str]:
    """`output.xfade` and `output.xfade_s` (plan 44 §3 D4, §5): rig controls
    like `output.dim` — group `output`, never persisted, not modulatable (a
    band on the fade would cut the room on every kick), learnable onto a
    fader — so they cross no file and an older build never sees them."""
    rig = {"group": "output", "persist": False, "modulatable": False}
    reg.continuous("output.xfade", "Deck fade", lambda: mix.xfade,
                   lambda v: setattr(mix, "xfade", min(1.0, max(0.0, float(v)))),
                   lo=0.0, hi=1.0, tip=XFADE_TIP, **rig)
    reg.continuous("output.xfade_s", "Fade seconds", lambda: mix.seconds,
                   lambda v: setattr(mix, "seconds", min(30.0, max(0.0, float(v)))),
                   lo=0.0, hi=30.0, tip=XFADE_S_TIP, **rig)
    return ["output.xfade", "output.xfade_s"]


def draw_size(full: tuple[int, int], cap: tuple[int, int] | None, fading: bool) -> tuple[int, int]:
    """The size a deck off air draws an output of size `full` at (plan 44 §8):
    the output's own during a fade (its frame then fits the render cap as the
    on-air deck's does), `preview_size` (under the cap, at most 1280 px on its
    long side) otherwise, what the panel's backdrop draws (`Fade.preview`)."""
    return (int(full[0]), int(full[1])) if fading else preview_size(full, cap)


def hand_over(main, off_air) -> None:
    """What the off-air deck's renderer reads this frame that the frame gave the
    on-air one: the bands, the window's ground and the render cap (§8: on both
    renderers). Its dim stays 1: the mix is laid before the on-air deck's dim. Its
    look — wiring, media, bus cuts, extra hands — is its own, and the rig's wires
    (the clouds, the hands' source, the poi) stand on both from `app.main`, so
    either deck can be on air."""
    off_air.bands = getattr(main, "bands", ())
    off_air.bg_alpha = getattr(main, "bg_alpha", 1.0)
    off_air.max_frame = getattr(main, "max_frame", None)
    off_air.dim = 1.0


# the fade at which a deck with a dream takes the worker, and how long after a
# fade the deck off air keeps its frame-sized targets (frames, 2 s at 60 Hz)
LEND_AT = 0.05
REST_FRAMES = 120
# what a warm draw draws at: small, since a compile does not depend on the size
WARM_SIZE = (64, 36)


def _spec_of(deck):
    """The graph `deck` has landed; a stand-in with none: None."""
    return getattr(getattr(deck, "graph", None), "spec", None)


def _dreams(deck) -> bool:
    """Does this deck's look use the dream worker now: a dream node in its
    graph, turned on?"""
    spec = deck.graph.spec
    return spec is not None and spec.dream is not None and bool(deck.renderer.dreamer.state.on)


class Fade:
    """The one mix between the deck on air and the other (plan 44 D4). `k` is the
    other's share of the picture, off `output.xfade`. Once a frame before the on-air
    deck draws: `begin_frame` (the dream worker's lend, and at 0 the fade's rest);
    above 0, the deck off air draws (`draw`) and each view carries its picture for
    `Renderer._compose` to mix. `targets` are its frame textures, one per output,
    let go `REST_FRAMES` after the fade with that deck's other frame-sized targets.
    Which deck is which reads through `pointer`, the meta controller's on air."""

    def __init__(self, on_air: Deck, off_air: Deck, mix: Mix, ctx=None, *, dream=None,
                 make_target: Callable[[Any], Any] = Offscreen, pointer: Pointer | None = None):
        self.decks = (on_air, off_air)
        self.pointer = pointer if pointer is not None else Pointer(on_air)
        self.mix, self.ctx = mix, ctx
        self.dream = dream
        self.make_target = make_target
        self.targets: list = []
        self.lent_to = self.rest = self.on_air  # who has the worker; the deck the fade left
        self.error = ""
        self.drew = False                  # did the deck off air's fade draw the last frame?
        self.previewed = False             # …or the panel's backdrop? (`preview`)
        self.first_ok = False              # did a fade's draw of the first view hold?
        self.shown = None                  # the `Preview` handed a fade's texture
        self.resting = REST_FRAMES         # frames at 0 since it last did
        self.warm_deck: Deck | None = None   # the deck to draw once (`ask_warm`)
        self.warm_error = ""               # what its last warm draw said, until the next
        self.said: Callable[[str], Any] | None = None   # told when a warm draw fails
        # each deck's graph as last told (`ask_warm`): a save lands no new one
        self.specs = {id(d): _spec_of(d) for d in self.decks}

    @property
    def on_air(self) -> Deck:
        return self.pointer.deck

    @property
    def off_air(self) -> Deck:
        return self.decks[1] if self.on_air is self.decks[0] else self.decks[0]

    @property
    def k(self) -> float:
        """The deck off air's share of the picture: 0 at the on-air deck's end of
        the fader, so that deck draws alone, by the bytes it draws alone."""
        x = self.mix.xfade
        return x if self.on_air is self.decks[0] else 1.0 - x

    def begin_frame(self) -> None:
        """The frame's start, whatever `k`: the lend; and at 0 what the fade
        said is forgotten, and after `REST_FRAMES` its frame-sized targets are
        let go (the render context is current)."""
        self.previewed = False
        self.lend()
        if self.k > 0.0:
            self.resting = 0
            return
        self.drew, self.error = False, ""
        if self.resting < REST_FRAMES:
            self.resting += 1
            if self.resting == REST_FRAMES:
                self.close()
                self.off_air.renderer.release_sized()

    def lend(self) -> None:
        """One dream worker (§2, row 558): at rest the on-air deck's, and in a fade
        the deck coming in's while its look has a dream on (`_dreams`) — from
        `LEND_AT` on and until the fader reaches an end, so a fader nudged or
        jittering at the bottom of its throw never wipes the on-air deck's dream,
        and on air moving at the middle, where neither deck stops being drawn,
        restarts nothing. The deck that gave it up holds its last dream. One
        comparison a frame until the answer moves."""
        k = self.k
        if k <= 0.0:
            self.rest = self.on_air
        rest = self.rest
        coming = self.decks[1] if rest is self.decks[0] else self.decks[0]
        share = k if coming is self.off_air else 1.0 - k
        take = k > 0.0 and _dreams(coming) and (self.lent_to is coming or share >= LEND_AT)
        to = coming if take else rest
        if to is self.lent_to:
            return
        self.lent_to = to
        if self.dream is None:
            return
        for d in self.decks:
            d.renderer.dreamer.source = self.dream if d is to else None
        self.dream.lend(to.reg)

    def ask_warm(self, deck: Deck) -> None:
        """A preset listener: a look landed on `deck`, or was saved, which landed no
        new graph and must not wipe a trail, so only a new graph counts. If `deck` is
        off air, draw it once at the next frame (`warm`), which is on the render
        context, as a copy or a load from the panel is not. A deck on air is drawn."""
        spec = _spec_of(deck)
        if spec is self.specs.get(id(deck)):
            return
        self.specs[id(deck)] = spec
        if deck is self.off_air:
            self.warm_deck = deck

    def warm(self, w: int, h: int, dpr: float, switches, samples: int | None = None) -> bool:
        """Once after a copy or a load: the deck off air drawn small and thrown
        away, so a shader's compile lands now and not in a fade's first frame (the
        reading's risk 3). Not above 0, where it is drawn anyway, nor once that deck
        has gone on air. Leaves nothing: its delays hold nothing again, its targets
        go. A raise stays on `warm_error` until the next warm draw, and `said` is
        told at once: this is the moment to learn it. True when it drew."""
        deck, self.warm_deck = self.warm_deck, None
        if deck is None or deck is not self.off_air or self.k > 0.0:
            return False
        r = deck.renderer
        tgt = self.make_target(self.ctx)
        why = ""
        try:
            hand_over(self.on_air.renderer, r)
            view = View(replace(switches, dim=1.0), WARM_SIZE, target=tgt.fit(WARM_SIZE),
                        viewport=(0, 0, *WARM_SIZE), samples=samples)
            r.draw_outputs(deck.view, w, h, dpr, [view])
            why = view.error or ""
        except Exception as e:  # noqa: BLE001 — the deck off air must not cost the on-air deck
            why = f"{type(e).__name__}: {e}"[:160]
        finally:
            tgt.release()
            r.reset_delays()
            r.release_sized()
        self.warm_error = f"warm draw: {why}" if why else ""
        if why and self.said is not None:
            self.said(f"the deck off air will not draw: {why}")
        return not why

    def preview(self, panel_view, w: int, h: int, dpr: float, full: tuple[int, int],
                switches) -> bool:
        """The deck off air for the panel's backdrop (`panel_view`, an
        `outputs.Preview`), after `draw`: a fade's own picture on a frame the deck
        already drew, since its delays turn once a frame (`render.py`), else one
        draw at `draw_size(full, cap, False)` into the preview's tap. A raise is
        said on `error`, and a frame that fails leaves the last picture lit. True when
        it published."""
        self.previewed = True
        if self.drew and self.targets:
            if not self.first_ok:
                return False
            panel_view.publish(self.targets[0].tex, 0.0)
            self.shown = panel_view         # (a texture of ours: `_forget_shown`)
            return True
        self.shown = None
        tap = panel_view.tap
        if tap is None:
            return False
        r = self.off_air.renderer
        self.resting = 0                   # its frame-sized targets rest as a fade's do
        try:
            hand_over(self.on_air.renderer, r)
            size = draw_size(full, r.max_frame, False)
            view = View(replace(switches, dim=1.0), size, target=tap.fit(size),
                        viewport=(0, 0, *size))
            r.draw_outputs(self.off_air.view, w, h, dpr, [view])
        except Exception as e:  # noqa: BLE001 — the deck off air must not cost the on-air deck
            self.error = f"{type(e).__name__}: {e}"[:160]
            return False
        if view.error:
            self.error = view.error
            return False
        panel_view.publish(tap.tex, 0.0)
        return True

    def draw(self, views: list[View], w: int, h: int, dpr: float,
             samples: int | None = None) -> bool:
        """Deck 2 onto a frame texture per view, at that view's size and
        through its switches at full dim; each view it drew then carries the
        picture and `k`. `samples`: the first view's scene sample count. True
        when it drew. At `k` 0 nothing runs; a raise is said on `error` and
        costs the on-air deck nothing (the views carry no mix)."""
        self.drew = False
        k = self.k
        if k <= 0.0:
            return False
        self.resting = 0
        r = self.off_air.renderer
        try:
            hand_over(self.on_air.renderer, r)
            while len(self.targets) < len(views):
                self.targets.append(self.make_target(self.ctx))
            sizes = [draw_size(v.size, r.max_frame, True) for v in views]
            drawn = [View(replace(v.switches, dim=1.0), sz, target=self.targets[i].fit(sz),
                          bg_alpha=v.bg_alpha, viewport=(0, 0, *sz),
                          samples=samples if i == 0 else None)
                     for i, (v, sz) in enumerate(zip(views, sizes, strict=True))]
            self._forget_shown()
            r.draw_outputs(self.off_air.view, w, h, dpr, drawn)
            self.first_ok = bool(drawn) and not drawn[0].error
            for i, (v, d) in enumerate(zip(views, drawn, strict=True)):
                if not d.error:
                    v.mix, v.mix_k = self.targets[i].tex, k
            self.error = next((d.error for d in drawn if d.error), "")
        except Exception as e:  # noqa: BLE001 — deck 2 must not cost the on-air deck
            self.error = f"{type(e).__name__}: {e}"[:160]
            return False
        self.drew = True
        return True

    def close(self) -> None:
        """Its frame textures let go (the render context current)."""
        for tgt in self.targets:
            tgt.release()
        self.targets = []
        self._forget_shown()

    def _forget_shown(self) -> None:
        """A `Preview` still showing a frame texture that has gone (a close, a
        resize) holds none: the page reads a black box, never a dead texture."""
        pv = self.shown
        if pv is not None and all(t.tex is not pv.tex for t in self.targets):
            pv.tex, self.shown = None, None
