"""Plan 44 D1 — the `Deck` (hyperspace/deck.py): today's singletons in one
bundle, built by `Deck.build` in `app.main`'s order, with no behaviour
change. The proof: a rig built the way `tests/test_undo.boot` built it
at 749be48 (a copy of that body, below) and one built through
`Deck.build` (today's `boot`) reach the same state over every corpus
preset; two registries share no frame state; `main` builds its deck once
with the frame order unchanged; and every swap target the deck lists
lives in a watched module, the deck itself included. Plan 44 D2 adds the
second comparison: one `Sources` fed once drives two routers over two
registries to the values one router over its own sources lands.

What differs, on purpose: the old `boot` had drifted from `main`. It
never handed the router its banks (`use_lfos` / `use_bank` /
`use_sequencer`, which `main` has called since plans 28 N0 and 31) and
built its `Undo` without `banks=`. Today's `boot` runs `main`'s lines, so
its LFOs, envelopes and sequencer step inside the pass and undo takes the
banks' membership. On three corpus presets (TRIP, TUMBLE, seq-demo) a
bank-driven row then leaves a base (`camera.zoom`, `view.bright`) a
round-off apart from the old rig's after the undo, because undo puts
back only a base that is not `undo.alike` its state (plan 15 §1 row 2).
`alike` is the right comparison for that case: it is the tolerance undo
itself uses to call two bases the same value. With main's three lines
added to the old body, the two rigs agree to the bit.
"""

from __future__ import annotations

import ast
import inspect
import json
import math
import textwrap
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import CORPUS, opened_last, seed
from test_app_boundary import ORDER, _host
from test_undo import DT, FakeIn, FakeOut, boot

from hyperspace import app, envelope, hands, lfo, routing, sequencer, tempo, undo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.bands import CEIL
from hyperspace.control import Control
from hyperspace.deck import Deck, in_patch
from hyperspace.fx import FxState
from hyperspace.ghost import GhostState
from hyperspace.hotreload import MODULES
from hyperspace.learn import Learn
from hyperspace.library import LOADABLE, Library, Marks
from hyperspace.lookback import DreamState
from hyperspace.midi import MidiIO
from hyperspace.overlay import Output
from hyperspace.params import Registry, build_registry, part_of
from hyperspace.loadable import LoadedPatch
from hyperspace.routing import Bindings, Router, Sources, bindings_path
from hyperspace.view import ViewState

PKG = Path(__file__).resolve().parents[1] / "hyperspace"
FRAMES = 120
SETTLE = math.ceil(undo.SETTLE_S / DT) + 3      # frames that close an undo step


def old_boot(home, show: str | None = None, *, fx=None, dream=None, ghost=None):
    """`tests/test_undo.boot` as it was at 749be48, before `Deck.build` —
    verbatim but for one line: the envelope bank and the sequencer are
    kept in names (`envs`, `seq`) so their state can be compared; the
    objects and the calls are the same."""
    seed(home)
    if show:
        opened_last(home, show)
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=True)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, audio, lib.project,
                         dream=dream if dream is not None else DreamState(),
                         fx=fx if fx is not None else FxState(),
                         ghost=ghost if ghost is not None else GhostState())
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    lib.on_load("band", control.scene_loaded)
    control.library = lib
    settings = hands.HandSettings.from_config({})
    hands.register(reg, settings)
    r = SimpleNamespace(t=100.0)
    clock = tempo.Clock(now=lambda: r.t)
    lfos = lfo.LFOs(seed=1)
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    # plan 31, as app.main: the envelopes and the sequencer beside the LFOs
    # (plan 36 T3: the factory `/7` files hold their values)
    envs, seq = envelope.Envelopes(), sequencer.Sequencer()     # (named: the one change)
    envelope.register(reg, envs, clock)
    sequencer.register(reg, seq, clock)
    output = Output(None, None)
    output.register(reg)
    # the desk's session params before attach, as app.main has them (plan 18
    # WP2): declared late, desk.slew would read as an unsaved show
    table = Bindings.load(bindings_path(home), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    # the panel's own params, declared as ui.Panel declares them (no imgui)
    from hyperspace.ui import Panel
    Panel._register_panel_params(SimpleNamespace(reg=reg, open=True, cheatsheet=True,
                                                 desk=True, page=1))
    router = Router(reg, table)
    loaded_patch = LoadedPatch(lib, reg, router)
    learn = Learn(reg, router.table, lane=router.lane)
    inp, out = FakeIn(), FakeOut()
    midi = MidiIO(reg, router.table, inp=inp, out=out, learner=learn)
    lib.project.load_startup()
    u = undo.Undo(reg, router.table, marks=Marks(lib), only=in_patch,
                  on_restore=router.sync_macros)
    undo.install(u)
    r.__dict__.update(lib=lib, reg=reg, view=view, control=control, chain=chain, audio=audio,
                      router=router, table=router.table, loaded_patch=loaded_patch, clock=clock,
                      lfos=lfos, learn=learn, midi=midi, inp=inp, out=out, undo=u,
                      home=Path(home), settings=settings, output=output, envs=envs, seq=seq)
    return r


def _frames(r, n: int) -> None:
    """`n` frames of the pass: the clock, undo's watcher, `router.modulate`
    over the fixed lanes the chain holds, then `reg.apply`."""
    for _ in range(n):
        r.t += DT
        r.clock.tick(r.t)
        r.undo.tick(r.t)
        r.router.modulate(r.chain, DT, r.t)
        r.reg.apply()


def _state(r) -> dict:
    """Everything the proof compares, as of now."""
    t, reg = r.table, r.reg
    groups = sorted({p.group for p in reg})
    return {
        "snapshot": {g: reg.snapshot(g) for g in groups},
        "table": json.dumps(t.to_json(), sort_keys=True),
        "routes": [b.to_json() for b in t.routes()],
        "desk": [b.to_json() for b in t.desk()],
        "macros": json.dumps(t.macros_doc(), sort_keys=True),
        "modifiers": json.dumps(t.modifiers_doc(reg), sort_keys=True),
        "lfos": list(r.lfos.doc()),
        "envs": list(r.envs.doc()),
        "labels": [s.label for s in r.undo.stack],
        "states": [s.before for s in r.undo.stack],
    }


def _walk(r) -> list[dict]:
    """Every corpus preset in turn: load it, 120 frames with one fixed lane
    vector, `view.bright` turned and settled into a step, `undo.undo()`."""
    names = sorted(r.lib.list(LOADABLE))
    files = sorted((CORPUS / "presets").glob("*.json"))
    assert len(names) == len(files) > 0
    out = []
    for i, name in enumerate(names):
        r.lib.load(LOADABLE, name)
        r.chain.out = CEIL * np.linspace(0.15, 0.85, len(r.chain.out))
        _frames(r, FRAMES)
        p = r.reg["view.bright"]
        p.set(p.lo + (p.hi - p.lo) * (0.25 + 0.5 * (i % 3) / 2))
        _frames(r, SETTLE)
        undo.undo()
        _frames(r, 2)
        out.append(_state(r))
    return out


def _same_state(a: undo.State, b: undo.State) -> bool:
    return (a.bases.keys() == b.bases.keys()
            and all(undo.alike(v, b.bases[k]) for k, v in a.bases.items())
            and a.routes == b.routes and a.desk == b.desk and a.macros == b.macros)


def _alike(a: dict, b: dict) -> bool:
    """Two snapshots: the same ids, each value equal within undo's tolerance."""
    return a.keys() == b.keys() and all(undo.alike(v, b[k]) for k, v in a.items())


def _compare(old: list[dict], new: list[dict], *, exact: bool) -> None:
    assert len(old) == len(new)
    for i, (a, b) in enumerate(zip(old, new, strict=True)):
        for key in ("table", "routes", "desk", "macros", "modifiers", "lfos", "envs",
                    "labels"):
            assert a[key] == b[key], f"preset {i}: {key} differs"
        if exact:
            assert a["snapshot"] == b["snapshot"], f"preset {i}: snapshot differs"
        else:
            assert a["snapshot"].keys() == b["snapshot"].keys()
            for g in a["snapshot"]:
                assert _alike(a["snapshot"][g], b["snapshot"][g]), f"preset {i}: {g} differs"
        assert len(a["states"]) == len(b["states"])
        assert all(_same_state(x, y) for x, y in zip(a["states"], b["states"], strict=True)), i


def test_a_deck_built_the_old_way_and_the_new_way_reach_the_same_state(tmp_path):
    """Plan 44 D1's proof: over one seeded home, the rig `boot` built at
    749be48 and the rig `Deck.build` builds (today's `boot`) land every
    corpus preset to the same registry, table, routes, desk, macros,
    modifiers, banks and undo stack — so the bundle changed nothing.

    One drift the old `boot` had from `main`, which this PR ends: it never
    handed the router its banks (`use_lfos` / `use_bank` /
    `use_sequencer`, which `main` has called since plans 28 N0 and 31), so
    its LFOs, envelopes and sequencer never stepped inside the pass. With
    those three lines added — what `main` ran — the old way and the deck
    are equal to the bit; without them, three presets (TRIP, TUMBLE,
    seq-demo) leave a base a round-off apart after the undo, which undo's
    own tolerance (`undo.alike`) calls the same value."""
    home = tmp_path / "home"
    new = _walk(boot(home))
    r = old_boot(home)
    r.router.use_lfos(r.lfos, r.clock)          # main's three lines at 749be48
    r.router.use_bank(r.envs, r.clock)
    r.router.use_sequencer(r.seq, r.envs)
    _compare(_walk(r), new, exact=True)
    _compare(_walk(old_boot(home)), new, exact=False)     # the old boot, verbatim


def _feed(src: Sources, t: float) -> None:
    """One frame of what the rig's sources say, into `src`: the hands'
    lanes (named, as the adapter publishes them) and the pad's axes, each
    a slow wave of its own; the analyzer's lanes are the chain's."""
    from hyperspace import gamepad
    from hyperspace.hands.core import Layout

    if "hand" not in src.names:
        lay = Layout(hands.HandSettings.from_config({}).axes)
        src.labels["hand"], src.gates["hand"] = lay.names, lay.gates
        src.names["hand"] = lay.index
        gamepad.publish(src)
    n = len(src.names["hand"])
    src.feed("hand", 0.5 + 0.45 * np.sin(t * (1.0 + 0.13 * np.arange(n))))
    k = len(gamepad.LANES)
    src.feed("axis", 0.5 + 0.4 * np.cos(t * (0.7 + 0.11 * np.arange(k))))


def _values(reg) -> dict:
    """Every param's effective value, as the frame left it — but the
    panel's own `ui.*`, whose getters read an imgui panel the headless rig
    stands in for with a namespace (none is a route's target)."""
    return {p.id: repr(p.value) for p in reg if p.group != "ui"}


def test_one_sources_fed_once_drives_two_routers_as_one_router_did(tmp_path):
    """Plan 44 D2's proof, the first thing decks promise: one `Sources`
    fed once a frame, two `Router`s over two registries both loaded with
    the same preset, and every param of the two lands the value one router
    over its own sources lands — every frame, over every corpus preset.
    The pass of each reads the shared feeds (the hands, the pad, the
    analyzer's chain) and steps its own banks, modifiers and followers."""
    solo = boot(tmp_path / "solo")
    a = boot(tmp_path / "a")
    shared = a.router.sources
    b = boot(tmp_path / "b", sources=shared)
    assert b.router.sources is shared and b.deck.sources is shared
    assert solo.router.sources is not shared
    assert a.reg is not b.reg and a.router is not b.router
    assert any(t is b.table.meta_table for t in shared.tables)
    rigs = (solo, a, b)
    names = sorted(a.lib.list(LOADABLE))
    assert names == sorted(solo.lib.list(LOADABLE)) == sorted(b.lib.list(LOADABLE))
    chain = a.chain                                  # one analyzer, as the rig has
    frames = 0
    driven: dict[str, set[str]] = {"hand": set(), "axis": set(), "lane": set()}
    for name in names:
        for r in rigs:
            r.lib.load(LOADABLE, name)
        chain.out = CEIL * np.linspace(0.15, 0.85, len(chain.out))
        for k in range(FRAMES // 2):
            for r in rigs:
                r.t += DT
                r.clock.tick(r.t)
            _feed(solo.router.sources, a.t)
            _feed(shared, a.t)                       # fed once for both routers
            for r in rigs:
                r.router.follow_macros()
                r.router.modulate(chain, DT, r.t)
                r.reg.apply()
            want = _values(solo.reg)
            assert _values(a.reg) == want, (name, k)
            assert _values(b.reg) == want, (name, k)
            frames += 1
        for row in a.table.mods():                   # what the shared feeds moved
            scheme = routing.base_scheme(row.scheme)
            p = a.reg.get(row.target)
            if scheme in driven and p is not None and p.modulated:
                driven[scheme].add(row.target)
    assert frames == len(names) * (FRAMES // 2)
    # the proof has teeth: the shared feeds drove params on both decks
    assert all(driven.values()), driven


def test_a_deck_beside_changes_nothing_on_air_and_lands_what_one_deck_lands(tmp_path):
    """Plan 44 D4, the same-state test extended. An empty deck beside the
    first, its pass and its apply in the frame in `app.frame`'s order, leaves
    the first where D1's walk leaves a deck alone, to the bit. And a deck
    beside the first loaded with the same preset lands, every frame of every
    corpus preset, the performance values a deck alone lands."""
    solo = _walk(boot(tmp_path / "solo"))
    r = boot(tmp_path / "with")
    beside = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    modulate, apply = r.router.modulate, r.reg.apply

    def both(*a, **k):
        modulate(*a, **k)
        apply()
        beside.router.modulate(*a, **k)
        beside.reg.apply()

    def no_apply():
        pass

    r.router.modulate, r.reg.apply = both, no_apply
    _compare(_walk(r), solo, exact=True)

    alone = boot(tmp_path / "alone")
    a = boot(tmp_path / "a")
    b = Deck.beside(a.deck, lfos=lfo.LFOs(seed=1))
    assert a.deck.sources is b.sources
    names = sorted(a.lib.list(LOADABLE))
    moved = 0

    def looks(reg) -> dict:
        return {p.id: repr(p.value) for p in reg if part_of(p) == "patch"}

    for name in names:
        doc = json.loads(Path(a.lib.path_of(LOADABLE, name)).read_text())
        alone.lib.load(LOADABLE, name)
        a.lib.load(LOADABLE, name)
        b.loaded_patch.load_doc(doc)
        alone.chain.out = a.chain.out = CEIL * np.linspace(0.15, 0.85, len(a.chain.out))
        for k in range(FRAMES // 2):
            for rr in (alone, a):
                rr.t += DT
                rr.clock.tick(rr.t)
            _feed(alone.router.sources, a.t)
            _feed(a.deck.sources, a.t)
            alone.router.follow_macros()
            alone.router.modulate(alone.chain, DT, alone.t)
            alone.reg.apply()
            a.router.follow_macros()
            b.router.follow_macros()
            a.router.modulate(a.chain, DT, a.t)
            a.reg.apply()
            b.router.modulate(a.chain, DT, a.t)
            b.reg.apply()
            want = looks(alone.reg)
            assert looks(b.reg) == want, (name, k)
            moved += b.reg["view.bright"].modulated
    assert moved > 0                             # the proof has teeth


def _mods(r) -> np.ndarray:
    """The ``mod`` vector a router's last pass left in its own lanes."""
    return np.array(r.router.feeds["mod"], dtype=float)


def test_two_routers_with_different_modifiers_each_keep_their_own_mod_lanes(tmp_path):
    """Plan 44 D2, review; D4 (row 591): the ``mod`` lanes are each router's
    own layer, and never in the shared sources. Two routers over one
    `Sources` with different modifiers (three on one, with a delay that
    reads last frame's lane, one on the other) each leave, after their
    own pass, exactly the lanes a router over its own sources leaves."""
    rigs = {k: boot(tmp_path / k) for k in ("solo_a", "solo_b", "a")}
    shared = rigs["a"].router.sources
    rigs["b"] = boot(tmp_path / "b", sources=shared)

    def wire(r, many: bool) -> None:
        t, reg = r.table, r.reg
        if many:
            t.add_modifier("smooth", ["lane:0"], reg, release=0.4)     # mod.1, with memory
            t.add_modifier("scale", ["mod:1"], reg, mul=0.5)           # mod.2
            t.add_modifier("delay", ["mod:2"], reg)                    # mod.3, a frame late
        else:
            t.add_modifier("scale", ["lane:1"], reg, mul=2.0)          # mod.1

    for k, r in rigs.items():
        wire(r, k.endswith("a"))
    chain = rigs["a"].chain
    for k in range(40):
        chain.out = CEIL * np.array([0.1 + 0.02 * (k % 9), 0.3 - 0.01 * (k % 7)]
                                    + [0.0] * (len(chain.out) - 2))
        for name in ("solo_a", "solo_b", "a", "b"):
            r = rigs[name]
            r.router.modulate(chain, DT, 100.0 + k * DT)
            r.reg.apply()
            solo = rigs["solo_" + name[-1]] if name in ("a", "b") else None
            if solo is not None:                 # straight after its own pass
                np.testing.assert_array_equal(_mods(r), _mods(solo), err_msg=f"{name} {k}")
                assert "mod" not in r.router.sources.feeds
    own_a, own_b = (rigs[k].router.lanes.feeds["mod"] for k in ("a", "b"))
    assert len(own_a) == 4 and len(own_b) == 2          # each router's vector, its size
    assert not np.isnan(own_a[3])                       # the delay ran on a's own lane


def test_a_clock_other_than_the_shared_sources_is_refused_before_anything_registers():
    """`Deck.build(sources=…, clock=…)` with two clocks: refused up front,
    before the registry, the banks or any hook exists — not halfway, from
    inside the router."""
    called = []
    with pytest.raises(ValueError, match="own clock"):
        Deck.build(library=None, control=None, audio=None,
                   table=lambda reg: called.append("table"),
                   hands=lambda reg: called.append("hands"),
                   sources=Sources(clock=tempo.Clock()), clock=tempo.Clock())
    assert called == []


def test_the_deck_holds_the_rig_boot_hands_out(tmp_path):
    """`boot`'s handles are the deck's objects; a headless deck has no GL:
    no renderer, and the installed undo is the deck's."""
    r = boot(tmp_path / "home")
    d = r.deck
    assert (d.reg, d.view, d.table, d.router, d.lfos, d.loaded_patch, d.learn, d.undo) == (
        r.reg, r.view, r.table, r.router, r.lfos, r.loaded_patch, r.learn, r.undo)
    assert d.table is d.router.table and d.graph is d.loaded_patch.graph
    assert d.renderer is None
    assert d.clock is r.clock is d.router.clock
    # plan 44 D2: the router reads the deck's sources (its own while there
    # is one deck), and the clock the banks step on is theirs
    assert d.sources is d.router.sources and d.sources.clock is d.clock
    assert d.sources.tables == [d.table.meta_table] and d.router.feeds.shared is d.sources.feeds
    assert undo.installed() is d.undo
    assert d.router.lfos is d.lfos and d.router.bank("env") is d.envs
    assert d.router.sequencer is d.seq and d.undo.marks is d.marks


def test_two_registries_share_no_frame_state():
    """`Registry.serial`, `frame` and `landed` are class-level defaults (a
    registry from before a hot reload has them); two registries diverge on
    the first write — the instance attribute, never the class's."""
    a, b = Registry(), Registry()
    assert (a.serial, a.frame, a.landed) == (b.serial, b.frame, b.landed) == (0, 0, None)
    a.toggle("t.a", "A", lambda: False, lambda v: None, group="ui")
    a.begin_frame()
    assert "serial" in vars(a) and "frame" in vars(a) and "landed" in vars(a)
    assert a.serial == 1 and a.frame == 1 and a.landed == 1
    assert (b.serial, b.frame, b.landed) == (0, 0, None)
    assert "serial" not in vars(b) and "frame" not in vars(b)
    assert (Registry.serial, Registry.frame, Registry.landed) == (0, 0, None)
    b.begin_frame()
    b.begin_frame()
    assert b.frame == 2 and a.frame == 1


def test_main_builds_its_deck_once_and_the_frame_order_is_unchanged():
    """`main` calls `Deck.build` once, the hooks at the rig's places, and
    hands `Host` the deck; `frame`'s order (test_app_boundary.ORDER) is
    what it was before D1 — `frame` reads the same flat handles."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(app.main)))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "build"
             and isinstance(n.func.value, ast.Name) and n.func.value.id == "Deck"]
    assert len(calls) == 1
    kw = {k.arg: ast.unparse(k.value) for k in calls[0].keywords}
    assert kw["hands"] == "hands_setup" and kw["outputs"] == "outputs_setup"
    assert kw["panel"] == "panel_setup" and kw["devices"] == "devices_setup"
    assert kw["renderer"] == "renderer" and kw["table"] == "load_table"
    assert kw["made"] == "made"
    # the hooks hand their objects on through `build` (RigMade), no shared
    # sentinels in `main`
    assert "nonlocal" not in inspect.getsource(app.main)
    # nothing of the deck's is still built in main
    src = inspect.getsource(app.main)
    for line in ("build_registry(", "Router(reg, table)", "LoadedPatch(library", "Learn(reg",
                 "undo.Undo(", "library.attach(reg)", "ViewState()"):
        assert line not in src, line
    assert "deck=deck" in src and "*deck.targets()" in src
    log: list[str] = []
    assert app.frame(_host(log), now=1.0, dt=1 / 60, fps=60.0) is True
    assert log == ORDER == [
        "clock.tick", "reloader.poll", "router.keys", "pad.poll", "router.pad",
        "router.claimed", "pad.lanes", "router.felt", "midi.poll", "bridge.reconnect",
        "media.poll", "router.follow_macros", "undo.tick", "output.apply", "mouse.poll",
        "audio.step", "audio.publish", "hands.poll", "bridge.receive", "bridge.publish",
        "router.modulate", "reg.apply", "table.sinks", "bridge.send_values",
        "view.integrate", "render.draw", "panel.draw"]


def test_the_build_keeps_mains_order():
    """`Deck.build`'s lines in the order `main` had them at 749be48: the
    registry, the band hooks, the hands, the clock and banks, the outputs,
    the table, attach, the panel, the router and its banks, the
    presets, learn, the devices, the startup preset, the marks and undo."""
    src = textwrap.dedent(inspect.getsource(Deck.build))
    src = src[src.index('"""', src.index('"""') + 3) + 3:]       # the body, not the docstring
    seq = ["s = ViewState()", "build_registry(s, control, audio, on_deck.project",
           "hands(reg)",
           "tempo.register(reg, clock)", "lfo.register(reg, lfos, clock)",
           "envelope.register(reg, envs, clock)", "sequencer.register(reg, seq, clock)",
           "made.outputs = outputs(reg)",
           "bindings = table(reg)", "library.attach(reg)", "panel(reg, s, clock=clock",
           "Router(reg, bindings, sources=sources)", "router.use_lfos(lfos, clock)",
           "router.use_bank(envs, clock)", "router.use_sequencer(seq, envs)",
           "LoadedPatch(on_deck, reg, router", "loaded_patch.graph.attach(renderer)",
           "Learn(reg, router.table", "devices(reg, router, learn, panel=",
           "library.project.load_startup()", "geometry.warm_all(first=s.shape)",
           "Marks(loaded_patch.lib)", "undos.Undo(reg, router.table", "undos.install(undo_obj)"]
    at = [src.index(s) for s in seq]
    assert at == sorted(at), [s for s, a, b in zip(seq, at, sorted(at), strict=True) if a != b]


def test_every_swap_target_lives_in_a_watched_module(tmp_path):
    """Audit H1 over `Deck.targets()`: each (object, module, class) names a
    watched module that defines the class, and the object is of it; `deck`
    itself is watched after `learn` and before `midi`."""
    import importlib

    r = boot(tmp_path / "home")
    targets = r.deck.targets()
    assert targets[0] == (r.deck, "deck", "Deck")                     # the deck itself first
    assert targets[1] == (r.view, "view", "ViewState")                # headless: no renderer
    defined: dict[str, set[str]] = {}
    for obj, mod, cls in targets:
        assert mod in MODULES, f"{mod}.{cls} is a swap target but {mod} is not watched"
        if mod not in defined:
            defined[mod] = {n.name for n in ast.parse((PKG / f"{mod}.py").read_text()).body
                            if isinstance(n, ast.ClassDef)}
        assert cls in defined[mod], f"{cls} is not defined in {mod}"
        assert type(obj) is getattr(importlib.import_module(f"hyperspace.{mod}"), cls)
    assert MODULES.index("learn") < MODULES.index("deck") < MODULES.index("midi")
    ids = [id(o) for o, _, _ in targets]
    assert len(ids) == len(set(ids))                                   # each object once


def test_a_save_of_deck_py_re_classes_the_live_deck_and_back_fills_a_new_field(
        tmp_path, monkeypatch):
    """The reloader over `Deck.targets()`: a save of deck.py that adds a
    field with a default re-classes the live deck to the new class and
    back-fills the field (`hotreload._backfill_dataclass`). The save is a
    copy of deck.py; the reloader's `importlib.reload` executes it into a
    fresh module object put in `sys.modules` (never re-executing the
    shared `hyperspace.deck` in place, which other tests and threads in
    the worker hold). Afterwards the deck's class and the back-filled
    attribute are put back, and monkeypatch restores the module entry, its
    `__file__` and the reloader's `importlib`, so the test leaves things
    as it found them."""
    import importlib.util
    import os
    import sys

    from hyperspace import hotreload
    from hyperspace.hotreload import HotReloader

    r = boot(tmp_path / "home")
    deck = r.deck
    mod = sys.modules["hyperspace.deck"]
    copy = tmp_path / "deck.py"
    src = (PKG / "deck.py").read_text()
    copy.write_text(src)
    monkeypatch.setattr(mod, "__file__", str(copy))     # the file the reloader watches

    def reload(m):
        spec = importlib.util.spec_from_file_location("hyperspace.deck", copy)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        monkeypatch.setitem(sys.modules, "hyperspace.deck", fresh)
        return fresh

    monkeypatch.setattr(hotreload, "importlib", SimpleNamespace(reload=reload))
    try:
        hot = HotReloader(deck.targets, modules=("deck",), period=0.0)
        assert "added" not in vars(deck)
        anchor = "    renderer: Any = None\n"
        assert src.count(anchor) == 1
        copy.write_text(src.replace(anchor, anchor + "    added: int = 7\n"))
        st = copy.stat()
        os.utime(copy, (st.st_atime, st.st_mtime + 5))
        assert hot.poll(now=1.0) and hot.error == "", hot.error
        fresh = sys.modules["hyperspace.deck"]
        assert fresh is not mod and type(deck) is fresh.Deck and type(deck) is not Deck
        assert deck.added == 7
        assert hot.status.startswith("hot: deck")
    finally:
        deck.__class__ = Deck
        vars(deck).pop("added", None)
    assert type(deck) is Deck and "added" not in vars(deck) and mod.Deck is Deck


def test_the_band_hooks_are_the_rigs_and_two_decks_leave_them_once(tmp_path, monkeypatch):
    """The library's band hooks and `control.library` are rig-to-rig wiring
    (plan 44 §2: the analyzer and the library are shared): the caller sets
    them once, before `Deck.build`, which never touches them — so a second
    deck over the same library (D2+) does not set them again."""
    from hyperspace.library import Library as Lib

    calls: list[str] = []
    ONCE = ["on_layout:band", "extra:band", "on_load:band"]

    def band() -> list[str]:          # the presets kind's own on_load is the deck's
        return [c for c in calls if c.endswith(":band")]

    for name in ("on_layout", "extra", "on_load"):
        real = getattr(Lib, name)
        monkeypatch.setattr(Lib, name, lambda self, group, hook, _n=name, _r=real: (
            calls.append(f"{_n}:{group}"), _r(self, group, hook))[1])
    r = boot(tmp_path / "home")
    assert band() == ONCE
    assert r.control.library is r.lib
    hooks = (r.lib._layout_hooks["band"], r.lib._extra_hooks["band"], r.lib._load_hooks["band"])
    startups: list = []
    real_startup = type(r.lib.project).load_startup
    monkeypatch.setattr(type(r.lib.project), "load_startup",
                        lambda self: (startups.append(1), real_startup(self))[1])
    loaded = r.lib.current(LOADABLE)
    # a second deck leaves the process's one-of-a-kind steps alone (plan 44
    # D1: `attach`, `startup`, `install` off; D2+ decides their real shape)
    second = Deck.build(library=r.lib, control=r.control, audio=r.audio,
                        table=lambda reg: Bindings(),
                        attach=False, startup=False, install=False, on_air=False)
    assert r.lib.reg is r.reg and undo.installed() is r.undo      # the first deck's still
    # (plan 44 D3: what is loaded is each deck's presets' own — the first's
    # is as it was; the kind stays the first until a pointer moves it, D5a)
    assert startups == [] and r.loaded_patch.current == loaded         # nothing re-landed
    assert second.loaded_patch.current is None and r.lib.loaded_patch is r.loaded_patch
    assert band() == ONCE                                                 # still once
    assert (r.lib._layout_hooks["band"], r.lib._extra_hooks["band"],
            r.lib._load_hooks["band"]) == hooks
    assert second.reg is not r.reg and r.control.library is r.lib
    src = textwrap.dedent(inspect.getsource(Deck.build))
    assert "on_layout" not in src and "control.library =" not in src
    main = inspect.getsource(app.main)
    assert main.index('library.on_layout("band"') < main.index("Deck.build(")
    assert main.index("control.library = library") < main.index("Deck.build(")


def test_a_renderer_and_a_stand_in_state_together_are_refused(tmp_path):
    """With a renderer the deck's params drive the renderer's own states;
    a `dream` / `fx` / `ghost` handed in beside it would be dropped, so
    `build` refuses it before building anything."""
    import pytest

    lib = Library(seed(tmp_path / "home"), period=0.0)
    chain = Analyzer(Analyser())
    renderer = SimpleNamespace(lookback=SimpleNamespace(state=DreamState()),
                               fx=SimpleNamespace(state=FxState()),
                               ghost=SimpleNamespace(state=GhostState()))
    for kw in ({"dream": DreamState()}, {"fx": FxState()}, {"ghost": GhostState()},
               {"fx": FxState(), "ghost": GhostState()}):
        with pytest.raises(ValueError, match=", ".join(kw)):
            Deck.build(library=lib, control=Control(chain), audio=SimpleNamespace(chain=chain),
                       table=lambda reg: Bindings(), renderer=renderer, **kw)


def test_the_panel_hook_gets_what_the_outputs_hook_returned(tmp_path):
    """The panel hook runs after the outputs hook and is handed its result
    (`output=`) with the clock and the banks, so the panel has
    its handles at the place `main` gave them before D1."""
    seen: dict = {}
    marker = object()
    lib = Library(seed(tmp_path / "home"), period=0.0)
    chain = Analyzer(Analyser())
    deck = Deck.build(library=lib, control=Control(chain), audio=SimpleNamespace(chain=chain),
                      table=lambda reg: Bindings(), outputs=lambda reg: marker,
                      panel=lambda reg, view, **kw: seen.update(kw, view=view))
    assert seen["output"] is marker and seen["view"] is deck.view
    assert (seen["clock"], seen["lfos"], seen["envs"], seen["seq"]) == (
        deck.clock, deck.lfos, deck.envs, deck.seq)
    seen.clear()
    Deck.build(library=lib, control=Control(chain), audio=SimpleNamespace(chain=chain),
               table=lambda reg: Bindings(), panel=lambda reg, view, **kw: seen.update(kw))
    assert seen["output"] is None                                       # no outputs hook


def test_the_hooks_hand_their_objects_on_and_into_the_record(tmp_path):
    """Each hook returns what it made; `build` hands the hands' setup and
    the panel to the devices hook and records every return on `made`, so
    `main` reads its rig objects from one record, not from sentinels."""
    from hyperspace.deck import DeckHooksMade

    lib = Library(seed(tmp_path / "home"), period=0.0)
    chain = Analyzer(Analyser())
    got: dict = {}
    made = DeckHooksMade()
    deck = Deck.build(library=lib, control=Control(chain), audio=SimpleNamespace(chain=chain),
                      table=lambda reg: Bindings(), hands=lambda reg: "settings",
                      outputs=lambda reg: "output", panel=lambda reg, view, **kw: "panel",
                      devices=lambda reg, router, learn, **kw: got.update(
                          kw, router=router, learn=learn) or "devices",
                      made=made)
    assert (made.hands, made.outputs, made.panel, made.devices) == (
        "settings", "output", "panel", "devices")
    assert got["panel"] == "panel" and got["hand_settings"] == "settings"
    assert got["router"] is deck.router and got["learn"] is deck.learn


def test_mains_hooks_name_a_missing_dependency():
    """`main`'s panel hook needs the outputs hook's Output and its devices
    hook the panel hook's Panel; each says so, naming the hook, rather
    than failing later on a None."""
    src = inspect.getsource(app.main)
    assert "the panel hook needs the outputs hook's Output" in src
    assert "the devices hook needs the panel hook's Panel" in src
