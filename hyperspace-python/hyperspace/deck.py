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
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from . import envelope, geometry, lfo, poi, sequencer, tempo, totem
from . import undo as undos
from .fx import FxState
from .ghost import GhostState
from .hold import Hold, preview_renderer, preview_size
from .hold import register as register_hold
from .learn import Learn
from .library import Marks, MetaMarks
from .lookback import DreamState
from .outputs import Offscreen, View
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
    `on_air`, off air `off_air`; when D5c's crossfader moves `on_air_pointer` it
    calls `place_players` and both duties go across. The keys and the mouse are
    no player's, nor is the panel. `on_players` is told when who holds what
    changes: a pad's rows name its player, so the device list reads it again."""

    def __init__(self, first: Deck, second: Deck, players: Players | None = None):
        self.decks = (first, second)
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
                deck = self.decks[0]
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
    """What `output.xfade` and `output.xfade_s` write: how far the outputs
    have gone over to the other deck, and the seconds a take will run it
    over (D5's; nothing reads it yet)."""

    xfade: float = 0.0
    seconds: float = 2.0


XFADE_TIP = ("Mixes the other deck's picture over this one's on every output, before "
             "the dim: 0 this deck alone, 1 the other deck alone. Never saved; nothing "
             "on the desk by default (the crossfader stays the master dim), learn it "
             "onto a fader.")
XFADE_S_TIP = "How long a take runs the fade, in seconds. 0 is a cut. Never saved."


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
    long side) otherwise — what D5's panel backdrop draws. In D4 nothing asks
    for the off-air picture, so off air the deck draws nothing at all."""
    return (int(full[0]), int(full[1])) if fading else preview_size(full, cap)


def hand_over(main, off_air) -> None:
    """What deck 2's renderer reads this frame that the on-air one was
    handed (the rig's: `hold.mirror`'s road, plan 44 §3 D4): the clouds, the
    bands, the hands' source and the poi, the window's ground and the render
    cap (§8: on both renderers). Its dim stays 1: the mix is laid before the
    on-air deck's dim. Its look — wiring, media, bus cuts, extra hands — is
    its own."""
    off_air.cloud_source = getattr(main, "cloud_source", None)
    off_air.poi_source = getattr(main, "poi_source", None)
    off_air.bands = getattr(main, "bands", ())
    off_air.bg_alpha = getattr(main, "bg_alpha", 1.0)
    off_air.max_frame = getattr(main, "max_frame", None)
    off_air.dim = 1.0
    g, og = getattr(main, "ghost", None), getattr(off_air, "ghost", None)
    if g is not None and og is not None:
        og.source = g.source


# the fade at which a deck with a dream takes the worker, and how long after a
# fade the deck off air keeps its frame-sized targets (frames, 2 s at 60 Hz)
LEND_AT = 0.05
REST_FRAMES = 120


def _dreams(deck) -> bool:
    """Does this deck's look use the dream worker now: a dream node in its
    graph, turned on?"""
    spec = deck.graph.spec
    return spec is not None and spec.dream is not None and bool(deck.renderer.dreamer.state.on)


class Fade:
    """The one mix between the on-air deck and the deck beside it (plan 44
    D4). `k` is `output.xfade`. Once a frame before the on-air deck draws:
    `begin_frame` (the dream worker's lend, and at 0 the fade's rest); above
    0, deck 2 draws (`draw`) and each view carries its picture for
    `Renderer._compose` to mix. `targets` are its frame textures, one per
    output, let go `REST_FRAMES` after the fade with deck 2's other
    frame-sized targets."""

    def __init__(self, on_air: Deck, off_air: Deck, mix: Mix, ctx=None, *, dream=None,
                 make_target: Callable[[Any], Any] = Offscreen):
        self.on_air, self.off_air, self.mix, self.ctx = on_air, off_air, mix, ctx
        self.dream = dream
        self.make_target = make_target
        self.targets: list = []
        self.lent_to = on_air
        self.error = ""
        self.drew = False                  # did deck 2 draw the last frame?
        self.resting = REST_FRAMES         # frames at 0 since it last did

    @property
    def k(self) -> float:
        return self.mix.xfade

    def begin_frame(self) -> None:
        """The frame's start, whatever `k`: the lend; and at 0 what the fade
        said is forgotten, and after `REST_FRAMES` its frame-sized targets are
        let go (the render context is current)."""
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
        """One dream worker (§2, row 558): the on-air deck's, and the deck
        going on air's while a fade is up and its look has a dream on
        (`_dreams`) — from `LEND_AT` on and until the fade is back at 0, so a
        fader nudged or jittering at the bottom of its throw never wipes the
        on-air deck's dream. The deck that gave it up holds its last dream.
        One comparison a frame until the answer moves."""
        k = self.k
        take = k > 0.0 and _dreams(self.off_air) and (self.lent_to is self.off_air or k >= LEND_AT)
        to = self.off_air if take else self.on_air
        if to is self.lent_to:
            return
        self.lent_to = to
        if self.dream is None:
            return
        for d in (self.on_air, self.off_air):
            d.renderer.dreamer.source = self.dream if d is to else None
        self.dream.lend(to.reg)

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
            r.draw_outputs(self.off_air.view, w, h, dpr, drawn)
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
