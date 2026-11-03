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
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import envelope, geometry, lfo, poi, sequencer, tempo, totem
from . import undo as undos
from .fx import FxState
from .ghost import GhostState
from .hold import Hold, preview_renderer
from .hold import register as register_hold
from .learn import Learn
from .library import Marks
from .lookback import DreamState
from .params import Registry, build_registry
from .preset import Presets
from .routing import Bindings, Router, Sources
from .view import ViewState


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

    @property
    def graph(self):
        """The presets' graph section (`preset.GraphSection`)."""
        return self.presets.graph

    @classmethod
    def build(cls, *, library, control, audio, table: Callable[[Registry], Bindings],
              renderer=None, media=None, restart: Callable[[], Any] | None = None,
              dream=None, fx=None, ghost=None,
              clock: tempo.Clock | None = None, lfos: lfo.LFOs | None = None,
              sources: Sources | None = None,
              hands: Callable[[Registry], Any] | None = None,
              outputs: Callable[[Registry], Any] | None = None,
              panel: Callable[..., Any] | None = None,
              devices: Callable[..., Any] | None = None,
              made: RigMade | None = None,
              attach: bool = True, startup: bool = True, install: bool = True,
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
        sources the router reads (plan 44 D2; new ones when None). The hooks, each called
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
        D2+ decides their real shape. `warm`: build every shape's geometry
        on a background thread once the startup preset has landed."""
        if renderer is not None:
            given = [k for k, v in (("dream", dream), ("fx", fx), ("ghost", ghost))
                     if v is not None]
            if given:
                raise ValueError(f"Deck.build: {', '.join(given)} given with a renderer, "
                                 "whose own states the deck's params must drive")
            dream, fx, ghost = renderer.lookback.state, renderer.fx.state, renderer.ghost.state
        s = ViewState()
        reg = build_registry(s, control, audio, library.project,
                             dream=dream if dream is not None else DreamState(),
                             fx=fx if fx is not None else FxState(),
                             ghost=ghost if ghost is not None else GhostState(),
                             media=media, restart=restart)
        made = made if made is not None else RigMade()
        if hands is not None:
            made.hands = hands(reg)            # before attach: "default" includes them
        # the tap-tempo clock and the LFO bank (tempo.py, lfo.py; four by
        # default, up to 16, plan 31 B): their knobs are params too, so a
        # preset carries a tempo and an LFO arrangement
        clock = clock if clock is not None else tempo.Clock()
        lfos = lfos if lfos is not None else lfo.LFOs()
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
        if renderer is not None:
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
        router = Router(reg, bindings, sources)
        router.use_lfos(lfos, clock)           # they step inside the pass (plan 28 N0)
        router.use_bank(envs, clock)           # …and so do the envelopes (plan 31)
        router.use_sequencer(seq, envs)        # after the banks begin, before the plan
        # the presets (preset.py): the library's `presets/` files, landed on the
        # registry and the table; the project's bank loads through it
        presets = Presets(library, reg, router)
        if renderer is not None:
            # plan 26 A4: a preset's graph section sets the renderer's wiring and
            # hands an extra hands node its own state (`Renderer.ghost_states`)
            presets.graph.attach(renderer)
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
        # launch starts with an empty stack: bases through the registry, table
        # parts through the table, what is loaded through the library's marks;
        # the bands' names in strip order say which layout a strip's values
        # belong to, and a restore tells the router its macros are acted on
        marks = Marks(library)
        undo_obj = undos.Undo(reg, router.table, marks=marks,
                              tag=lambda: tuple(s.name for s in audio.chain.spec),
                              on_restore=router.sync_macros,
                              # the LFOs' membership (plan 31 B), read off the
                              # router at each step, so a re-classed router counts
                              banks=lambda: router._banks())
        if install:
            undos.install(undo_obj)        # what undo.push and the edit.* triggers reach
        if hold is not None:
            hold.undo = undo_obj           # Drop goes back to the hold's point through it
        return cls(reg=reg, view=s, table=router.table, router=router, lfos=lfos, envs=envs,
                   seq=seq, clock=clock, presets=presets, learn=learn, undo=undo_obj, marks=marks,
                   renderer=renderer, hold=hold, sources=sources)

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
