"""Plan 44 D4: deck 2 beside the first and `output.xfade`, the one mix pass.

Headless: deck 2 over the first deck's meta controller, sources and clock; nothing
writes it, no file moves; each deck's lanes its own (row 591); the lead's
meta controller offsets land the frame of its pass, a deck off air's rows on one are
dormant and it reads this frame's value (rows 625, 650); `Fade` over stand-ins.
GL (the `ctx` fixture): xfade 1 is deck 2's bytes, 0.5 white over black is
half within one 8-bit step, a raise in deck 2's draw costs the on-air deck
nothing, and the mix comes before the dim.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from test_undo import DT, boot

from hyperspace import app, envelope, lfo, modifiers, routing, sequencer
from hyperspace.analyzer import CEIL
from hyperspace.deck import (
    LEND_AT,
    REST_FRAMES,
    Deck,
    Fade,
    Mix,
    draw_size,
    hand_over,
    register_xfade,
)
from hyperspace.library import LOADABLE
from hyperspace.media.channels import Channels, MediaSources
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.routing_sources import DECK_SCHEMES, Layered, Sources


def _pair(tmp_path):
    a = boot(tmp_path / "a")
    return a, Deck.beside(a.deck)


def _pass(*pairs, chain=None, t=100.0):
    """One frame's pass in `app.frame`'s order: the lead's, then each deck
    off air's, each with its apply."""
    for router, reg in pairs:
        router.modulate(chain, DT, t)
        reg.apply()


# ------------------------------------------------------------ the second deck

def test_a_deck_beside_shares_the_meta_and_holds_its_own_look(tmp_path):
    a, b = _pair(tmp_path)
    assert b.meta_reg is a.deck.meta_reg and b.sources is a.deck.sources
    assert b.clock is a.deck.clock and b.table.meta_table is a.table.meta_table
    assert b.reg is not a.reg and b.view is not a.view and b.router is not a.router
    assert b.lfos is not a.lfos and b.undo is not a.deck.undo and b.loaded_patch is not a.deck.loaded_patch
    assert b.reg["output.dim"] is a.reg["output.dim"]             # the room's, by reference
    assert b.reg["view.bright"] is not a.reg["view.bright"]       # the look's, its own
    assert a.deck.meta_reg.on_air_reg is a.reg                           # the first stays the lead


def test_a_deck_beside_leaves_the_library_the_strip_and_undo_with_the_first(tmp_path):
    from hyperspace import undo

    a, b = _pair(tmp_path)
    lib = a.lib
    assert lib.loaded_patch is a.deck.loaded_patch
    assert undo.installed() is a.deck.undo
    before = a.reg["view.bright"].value
    b.reg["view.bright"].set(0.123)
    assert a.reg["view.bright"].value == before
    names = sorted(lib.list(LOADABLE))
    lib.load(LOADABLE, names[0])
    assert lib.current(LOADABLE) == names[0] == a.deck.loaded_patch.current
    assert b.loaded_patch.current is None and b.table.routes() == []


def test_nothing_of_a_deck_beside_writes_a_file(tmp_path):
    a, b = _pair(tmp_path)
    home = tmp_path / "a"

    def files():
        return {p: p.read_bytes() for p in home.rglob("*") if p.is_file()}

    before = files()
    chain = a.chain
    for k in range(30):
        _pass((a.router, a.reg), (b.router, b.reg), chain=chain, t=100.0 + k * DT)
        b.view.integrate(DT)
    assert files() == before


def test_the_mix_controls_are_meta_controls_that_nothing_saves():
    from hyperspace.params import Registry, part_of

    reg, mix = Registry(), Mix()
    assert register_xfade(reg, mix) == ["output.xfade", "output.xfade_s"]
    fade, secs = reg["output.xfade"], reg["output.xfade_s"]
    for p in (fade, secs):
        assert p.group == "output" and not p.persist and not p.modulatable
        assert part_of(p) == "shared_meta"
    fade.set(0.25)
    secs.set(3.0)
    assert (mix.xfade, mix.seconds) == (0.25, 3.0)
    fade.set(2.0)
    assert mix.xfade == 1.0
    assert reg.snapshot("output") == {}


def test_the_crossfader_is_the_decks_and_master_the_dim():
    """The owner, 2026-11-04, overturning row 559: a DJ mixer's crossfader, the MASTER
    fader the dim, and `master.gain` on the panel with no desk row."""
    from hyperspace import apc40

    rows = {b.source: b.target for b in Bindings.factory().bindings}
    assert rows[f"cc:0:{apc40.CC_XFADE}"] == "output.xfade"
    assert rows[f"cc:0:{apc40.CC_MASTER}"] == "output.dim"
    assert "master.gain" not in rows.values()


# ----------------------------------------------- each deck its own lanes (591)

def test_the_deck_schemes_are_the_banks_and_the_modifiers():
    assert DECK_SCHEMES == {lfo.LFOs.SCHEME, envelope.Envelopes.SCHEME, sequencer.GROUP,
                            modifiers.SCHEME}
    assert DECK_SCHEMES == set(routing.BUILTIN_LANES) - {"lane"} | {modifiers.SCHEME}


def test_each_deck_has_its_own_lanes_and_the_sources_hold_none_of_them(tmp_path):
    """Row 591, changed: two decks' LFOs and modifiers publish into their own
    layers; what the panel reads between passes is its own deck's, whichever
    ran last, and the shared sources hold no deck's lanes."""
    a, b = _pair(tmp_path)
    a.table.add_modifier("scale", ["lane:0"], a.reg, mul=0.5)
    a.table.add_modifier("scale", ["lane:1"], a.reg, mul=0.5)
    b.table.add_modifier("scale", ["lane:2"], b.reg, mul=2.0)
    a.chain.out = CEIL * np.linspace(0.1, 0.9, len(a.chain.out))
    b.reg["lfo.1.rate"].set(0.5 * a.reg["lfo.1.rate"].value + 0.3)
    _pass((a.router, a.reg), (b.router, b.reg), chain=a.chain)
    for scheme in DECK_SCHEMES:
        assert scheme not in a.deck.sources.feeds
        assert scheme not in a.deck.sources.labels
    assert len(a.router.feeds["mod"]) == 3 and len(b.router.feeds["mod"]) == 2
    assert a.router.labels["mod"] != b.router.labels["mod"]
    assert a.router.feeds["lfo"] is not b.router.feeds["lfo"]
    assert "mod" in a.router.schemes() and "mod" in b.router.schemes()


def test_a_row_reads_its_own_decks_lfo_not_the_other_decks(tmp_path):
    """The rests and the feeds a row reads are its own deck's: two decks with
    their LFOs apart each land what they would alone."""
    solo = boot(tmp_path / "solo")
    a, b = _pair(tmp_path)
    for r in (solo, a):
        r.table.add(Binding("lfo:0", "view.bright", "push", 0.5))
        r.reg["lfo.1.depth"].set(1.0)
    b.table.add(Binding("lfo:0", "view.bright", "push", 0.5))
    b.reg["lfo.1.depth"].set(0.0)        # at rest: its route adds nothing
    was = b.reg["view.bright"].value
    moved = set()
    for k in range(40):
        t = 100.0 + k * DT
        solo.router.modulate(solo.chain, DT, t)
        solo.reg.apply()
        _pass((a.router, a.reg), (b.router, b.reg), chain=a.chain, t=t)
        assert a.reg["view.bright"].value == pytest.approx(solo.reg["view.bright"].value)
        assert b.reg["view.bright"].value == pytest.approx(was)
        moved.add(round(a.reg["view.bright"].value, 4))
    assert len(moved) > 3


def test_a_scheme_no_layer_holds_falls_through_to_the_sources():
    src = Sources()
    r = Router_stub(src)
    src.feed("lfo", [0.25])                 # a bare feed, no bank
    src.feed("hand", [0.5])
    assert r.feeds.get("lfo")[0] == 0.25 and r.feeds["hand"][0] == 0.5
    r.feed("lfo", [0.75])
    assert r.feeds["lfo"][0] == 0.75 and src.feeds["lfo"][0] == 0.25
    r.feed("hand", [0.1])                   # a rig scheme, fed through the router
    assert src.feeds["hand"][0] == 0.1
    r.labels["hand"] = ["x"]
    assert src.labels["hand"] == ["x"]
    assert sorted(Layered({"a": 1}, {"a": 2, "b": 3})) == ["a", "b"]
    assert len(Layered({"a": 1, "c": 4}, {"a": 2, "b": 3})) == 3


def Router_stub(src):
    from hyperspace.params import Registry

    return Router(Registry(), Bindings([]), sources=src)


# ----------------------------------------------- the pass order (row 625)

def test_the_leads_offset_lands_in_the_frame_of_its_pass(tmp_path):
    a, b = _pair(tmp_path)
    a.table.set_routes([])               # (the startup loadable patch's own hand rows)
    p = a.reg["view.bright"]
    p.set(p._value_of_norm(0.25))
    was = p.norm
    a.deck.sources.feed("hand", [1.0])
    a.table.add(Binding("hand:0", "view.bright", "push", 0.25))
    _pass((a.router, a.reg), (b.router, b.reg), chain=a.chain)
    assert p.eff_norm == pytest.approx(was + 0.25)   # this frame, not the next


def test_no_deck_takes_a_row_on_a_meta_param_and_one_left_standing_is_dormant(tmp_path):
    """Register row 743: no deck's door takes a row onto a shared meta param, so one
    loadable patch cannot reach through the room to the other. A hot reload can leave one
    in the live table until the next load (row 745): off air it stays dormant
    (row 650), and it acts only on the lead, as before."""
    a, b = _pair(tmp_path)
    for t in (a.table, b.table):
        with pytest.raises(ValueError, match="master.gain is the meta controller's"):
            t.add(Binding("hand:0", "master.gain", "push", 0.25))
        assert not t.routes_to("master.gain")
    a.table.set_routes([])               # (the startup loadable patch's own hand rows)
    p = a.reg["master.gain"]
    p.set(p._value_of_norm(0.25))
    was = p.norm
    a.deck.sources.feed("hand", [1.0])
    b.table.bindings.append(Binding("hand:0", "master.gain", "push", 0.25))
    _pass((a.router, a.reg), (b.router, b.reg), chain=a.chain)
    assert p.eff_norm == pytest.approx(was) and not p.modulated


def test_a_deck_off_air_reads_this_frames_meta_values(tmp_path):
    """The lead first: a route of the deck off air scaled by a shared meta param
    the desk moved reads the value that landed this frame."""
    a, b = _pair(tmp_path)
    p = a.reg["master.gain"]
    p.set(p._value_of_norm(0.5))
    a.chain.out = CEIL * np.ones_like(a.chain.out)
    b.table.add(Binding("lane:0", "view.bright", "push", 0.0625, scale="master.gain"))
    q = b.reg["view.bright"]
    q.set(q._value_of_norm(0.25))
    base = q.norm
    _pass((a.router, a.reg), (b.router, b.reg), chain=a.chain)
    assert q.eff_norm == pytest.approx(base + 0.0625 * float(p.value), rel=1e-6)


def test_a_macro_on_a_deck_off_air_never_writes_a_meta_base(tmp_path):
    """Review finding 2: `follow_macros` runs off air now, and a meta controller base
    is the lead's. Its own params still follow."""
    a, b = _pair(tmp_path)
    p, own = a.reg["master.gain"], b.reg["view.bright"]
    was, own_was = p.base, own.base
    b.table.macros = {"macro.1": routing.Macro("m", [routing.Sub(base="master.gain"),
                                                     routing.Sub(base="view.bright")])}
    b.reg["macro.1"].set(0.5)
    assert b.router.follow_macros(force=True) == ["view.bright"]
    assert p.base == was and own.base != own_was


def test_a_deck_schemes_rests_reach_the_feel_and_the_row(tmp_path, monkeypatch):
    """Review finding 10: `felt` read the sources' rests, so a deck scheme's
    read 0."""
    seen = []

    class Rec(routing.Follower):
        __slots__ = ()

        def step(self, target, dt, m, rest=0.0):
            seen.append(rest)
            return float(target)

    monkeypatch.setattr(routing, "Follower", Rec)
    r = Router_stub(Sources())
    r.source_feel = lambda scheme: routing.Motion()
    r.rests["lfo"] = [0.5]
    r.felt("lfo", [0.25], DT)
    assert seen == [0.5]


# --------------------------------------------------------- media: read once

class _Feed:
    timed = False
    kind = "syphon"
    status = "ok"
    duration = 0.0
    audio = None

    def __init__(self):
        self.polls = 0

    def open(self):
        pass

    def close(self):
        pass

    def gl_poll(self):
        self.polls += 1
        if self.polls > 1:
            return None         # as a Syphon feed asked twice: no new frame
        return MediaFrame(np.zeros((2, 2, 4), dtype=np.uint8), 0.0, self.polls)


def test_each_channel_is_read_once_a_frame_and_both_decks_get_the_same_frame():
    feed = _Feed()
    src = MediaSources(opener=lambda sid, resolver: feed)
    one, two = Channels(sources=src), Channels(sources=src)
    for c in (one, two):
        c.channels["a"].source = feed
    src.begin_frame()
    got = one.frame("a")
    assert got is not None and two.frame("a") is got and one.frame("a") is got
    assert feed.polls == 1
    src.begin_frame()                   # the next frame asks again
    one.frame("a")
    assert feed.polls == 2


def test_with_no_frame_begun_a_read_is_a_fresh_read():
    feed = _Feed()
    src = MediaSources()
    c = Channels(sources=src)
    c.channels["a"].source = feed
    c.frame("a")
    c.frame("a")
    assert feed.polls == 2


def test_a_deck_off_air_leaves_the_mixer_alone():
    fed = []
    src = MediaSources()
    src.mixer = SimpleNamespace(feed=lambda voices, asked: fed.append(asked), close=lambda b: True)
    src._mixer = lambda: src.mixer
    Channels(sources=src).poll(DT, 1.0, heard=False)
    assert fed == []
    Channels(sources=src).poll(DT, 1.0)
    assert fed == [False]


def test_the_media_side_polls_the_decks_off_air_on_one_read():
    log: list[str] = []
    state = SimpleNamespace(sources=SimpleNamespace(begin_frame=lambda: log.append("begin")),
                            poll=lambda dt, now, heard: log.append(f"on air {heard}"),
                            close=lambda: None)
    other = SimpleNamespace(poll=lambda dt, now, heard: log.append(f"off air {heard}"),
                            drop_sources=lambda: log.append("drop"))
    io = app.MediaIO(SimpleNamespace(stop=lambda: None), state)
    io.off_air.append(other)
    io.poll(DT, 1.0)
    assert log == ["begin", "off air False", "on air True"]


# ------------------------------------------------------- the size, the handover

def test_the_off_air_size_is_the_preview_and_the_fade_the_output():
    assert draw_size((3840, 2160), (1920, 1080), True) == (3840, 2160)
    assert draw_size((3840, 2160), (1920, 1080), False) == (1280, 720)
    assert draw_size((3840, 2160), None, False) == (1280, 720)
    assert max(draw_size((5000, 1000), None, False)) == 1280
    assert draw_size((800, 600), None, False) == (800, 600)


def test_both_renderers_are_under_the_render_cap_and_deck_2_keeps_full_dim():
    main = SimpleNamespace(cloud_source=None, poi_source=None, bands=(0.5,), bg_alpha=0.5,
                           max_frame=(1920, 1080), dim=0.3,
                           ghost=SimpleNamespace(source=None))
    # the meta controller's wires stand on both from `app.main` (D5c): an on-air deck with none
    # takes nothing from one that has them
    r = SimpleNamespace(ghost=SimpleNamespace(source="hands"), wiring="its own", media="its own",
                        cloud_source="clouds", poi_source="poi")
    hand_over(main, r)
    assert r.max_frame == (1920, 1080) and r.dim == 1.0 and r.bg_alpha == 0.5
    assert r.bands == (0.5,)
    assert (r.cloud_source, r.poi_source, r.ghost.source) == ("clouds", "poi", "hands")
    assert r.wiring == "its own" and r.media == "its own"


# ------------------------------------------------------- the fade over stand-ins

class _R:
    bg_alpha, max_frame, dim = 1.0, None, 1.0
    bands = ()

    mix_error = ""

    def __init__(self, log, name, boom=False):
        self.log, self.name, self.boom = log, name, boom
        self.ghost = SimpleNamespace(source=None)
        self.dreamer = SimpleNamespace(source=None, state=SimpleNamespace(on=True))
        self.calls = []
        self.released = 0

    def release_sized(self):
        self.released += 1

    def draw_outputs(self, s, w, h, dpr, views, t_now=None):
        self.log.append(f"draw {self.name}")
        self.calls.append(views)
        if self.boom:
            raise RuntimeError("deck 2 is broken")


class _Target:
    def __init__(self, ctx):
        self.tex = SimpleNamespace(size=None)
        self.sizes = []
        self.released = 0

    def fit(self, size):
        self.sizes.append(size)
        self.tex.size = size
        return f"fbo{size}"

    def release(self):
        self.released += 1


def _fade(log, k=0.0, dream=None, boom=False, dreams=True):
    a = SimpleNamespace(renderer=_R(log, "a"), reg="reg a", view="view a")
    b = SimpleNamespace(renderer=_R(log, "b", boom), reg="reg b", view="view b",
                        graph=SimpleNamespace(spec=SimpleNamespace(
                            dream="node" if dreams else None)))
    a.renderer.dreamer.source = dream
    return Fade(a, b, Mix(xfade=k), None, dream=dream, make_target=_Target)


def _draw(monkeypatch, fade, log, n=1):
    from test_app_boundary import _Ctx, _rig_slots, _SwapGlfw

    monkeypatch.setattr(app, "glfw", _SwapGlfw(log, {"w1": (1600, 1000)}))
    monkeypatch.setattr(app, "_samples_of", lambda ctx, fbo: 4)
    slots = _rig_slots(*("x" * n))
    slots[0].switches.flip_x, slots[0].switches.dim = True, 0.4
    app._draw_render(fade.on_air.renderer, _Ctx(log), object(), slots, flush=lambda: None,
                     fade=fade)
    return slots


def test_at_xfade_0_deck_2_draws_nothing(monkeypatch):
    log: list[str] = []
    fade = _fade(log)
    _draw(monkeypatch, fade, log)
    assert "draw b" not in log and fade.off_air.renderer.calls == [] and fade.targets == []
    views = fade.on_air.renderer.calls[0]
    assert views[0].mix is None and views[0].mix_k == 0.0
    assert not fade.drew


def test_above_0_deck_2_draws_first_and_each_view_carries_its_picture(monkeypatch):
    log: list[str] = []
    fade = _fade(log, 0.25)
    _draw(monkeypatch, fade, log)
    assert log.index("draw b") < log.index("draw a")
    assert log.index("bind screen", log.index("draw b")) < log.index("draw a")   # rebound
    view = fade.off_air.renderer.calls[0][0]
    # at the output's size, through its switches, at full dim: the dim is the on-air deck's
    assert view.size == (1600, 1000) and view.switches.flip_x and view.switches.dim == 1.0
    onair = fade.on_air.renderer.calls[0][0]
    assert onair.switches.dim == 0.4
    assert onair.mix is fade.targets[0].tex and onair.mix_k == 0.25
    assert fade.drew


def test_a_raise_in_deck_2s_draw_costs_the_on_air_deck_nothing(monkeypatch):
    log: list[str] = []
    fade = _fade(log, 0.5, boom=True)
    _draw(monkeypatch, fade, log)
    assert "draw a" in log
    view = fade.on_air.renderer.calls[0][0]
    assert view.mix is None
    assert "deck 2 is broken" in fade.error and not fade.drew


def test_the_one_dream_worker_is_lent_for_the_fade_and_back():
    lent = []
    worker = SimpleNamespace(lend=lent.append)
    fade = _fade([], 0.0, dream=worker)
    a, b = fade.on_air.renderer, fade.off_air.renderer
    fade.lend()
    assert lent == [] and a.dreamer.source is worker and b.dreamer.source is None
    fade.mix.xfade = LEND_AT
    fade.lend()
    fade.lend()                                  # once a fade
    assert lent == ["reg b"] and b.dreamer.source is worker and a.dreamer.source is None
    fade.mix.xfade = 0.02                        # on its way down: still lent
    fade.lend()
    assert lent == ["reg b"]
    fade.mix.xfade = 0.0
    fade.lend()
    assert lent == ["reg b", "reg a"] and a.dreamer.source is worker and b.dreamer.source is None


def test_a_fader_at_the_bottom_of_its_throw_leaves_the_dream_alone():
    lent = []
    worker = SimpleNamespace(lend=lent.append)
    fade = _fade([], 0.0, dream=worker)
    for k in (0.02, 0.0, 0.04, 0.0, 0.01):
        fade.mix.xfade = k
        fade.lend()
    assert lent == [] and fade.on_air.renderer.dreamer.source is worker


@pytest.mark.parametrize("why", ["no node", "off"])
def test_a_deck_with_no_dream_on_never_takes_the_worker(why):
    lent = []
    worker = SimpleNamespace(lend=lent.append)
    fade = _fade([], 1.0, dream=worker, dreams=why != "no node")
    fade.off_air.renderer.dreamer.state.on = why != "off"
    fade.on_air.renderer.dreamer.source = worker
    fade.lend()
    assert lent == [] and fade.on_air.renderer.dreamer.source is worker


def test_back_at_0_the_system_page_forgets_the_fade_and_its_targets_go():
    log: list[str] = []
    fade = _fade(log, 0.5)
    fade.draw([View(Switches(), (8, 8), target="t")], 8, 8, 1.0)
    fade.error = "stale"
    assert fade.drew and len(fade.targets) == 1
    tgt = fade.targets[0]
    fade.begin_frame()
    assert fade.drew and fade.resting == 0       # still up
    fade.mix.xfade = 0.0
    fade.begin_frame()
    assert not fade.drew and fade.error == ""
    assert fade.targets == [tgt]                 # a fader back up at once finds them
    for _ in range(REST_FRAMES):
        fade.begin_frame()
    assert fade.targets == [] and tgt.released == 1
    assert fade.off_air.renderer.released == 1   # once
    assert fade.resting == REST_FRAMES


def test_no_worker_is_nothing_to_lend():
    fade = _fade([], 0.5)
    fade.lend()
    assert fade.lent_to is fade.off_air and fade.off_air.renderer.dreamer.source is None


def test_the_worker_lent_dreams_with_the_borrowers_params_from_a_clean_buffer():
    """`DreamWorker.lend` (dream.py): `dream.*` read from the borrower, the
    dream restarts on the new deck's frame, and nothing of the last deck's is
    published as the new deck's."""
    dream = pytest.importorskip("hyperspace.dream")
    pytest.importorskip("torch")
    from hyperspace.params import Registry

    def reg_with(k):
        r = Registry()
        r.continuous("dream.k", "k", lambda: k, lambda v: None, lo=0.0, hi=1.0, group="dream")
        return r

    a, b = reg_with(0.5), reg_with(0.25)
    w = dream.DreamWorker(a, {"device": "cpu"}, step_fn=lambda D, mask, p: D, start=False)
    shape = (4, 4, 4)
    w.submit(np.full(shape, 255, dtype=np.uint8), 1)
    job = w._pending
    assert job.params["k"] == 0.5
    w._pending = None
    w._process(job)
    assert w.latest() is not None
    assert float(w.D.mean()) > 0.9
    w.submit(np.full(shape, 255, dtype=np.uint8), 2)
    stale = w._pending
    w.lend(b)
    assert w._pending is None and w.latest() is None and w.reg is b
    w._process(stale)
    assert w.latest() is None                    # the last deck's frame publishes nothing
    # …nor one lent out from under it mid-step: the check is at the publish
    w.submit(np.full(shape, 255, dtype=np.uint8), 3)
    running, w._pending = w._pending, None
    step = w.step_fn

    def lent_mid_step(D, mask, p):
        w.lend(b)
        return step(D, mask, p)

    w.step_fn = lent_mid_step
    w._process(running)
    w.step_fn = step
    assert w.latest() is None
    w.submit(np.zeros(shape, dtype=np.uint8), 1)
    job = w._pending
    assert job.params["k"] == 0.25
    w._pending = None
    w._process(job)
    assert float(w.D.mean()) == 0.0              # afresh from the borrower's frame
    assert w.latest() is not None


def test_the_system_page_shows_a_second_gpu_block_and_nothing_else_of_deck_2():
    from hyperspace.ui import Panel

    p = SimpleNamespace(fade=None)
    assert Panel.deck2_gpu_lines(p) == []
    fade = _fade([], 0.5)
    p.fade = fade
    assert Panel.deck2_gpu_lines(p) == ["deck 2: off air, draws nothing"]
    fade.drew = True
    fade.off_air.renderer.stats = {"gpu_ms": {"scene": 1.5}, "ends": ["shown(scene)"]}
    lines = Panel.deck2_gpu_lines(p)
    assert lines[0].startswith("deck 2 gpu per node") and "scene" in lines[1]
    fade.error = "boom"
    assert Panel.deck2_gpu_lines(p)[-1] == "deck 2: boom"
    fade.on_air.renderer.mix_error = "mix: refused"      # a dead fader is said
    assert Panel.deck2_gpu_lines(p)[-1] == "deck 2: mix: refused"


# ---------------------------------------------------------------- the real pass

def _solid(ctx, size, rgba):
    tex = ctx.texture(size, 4)
    tex.write(np.tile(np.array(rgba, dtype=np.uint8), (size[1], size[0], 1)).tobytes())
    return tex


def _target(ctx, size, rgba):
    tex = _solid(ctx, size, rgba)
    return tex, ctx.framebuffer(color_attachments=[tex])


def _renderer(ctx):
    from hyperspace.render import Renderer
    return Renderer(ctx)


def _read(fbo, size):
    return np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(size[1], size[0], 4)


def test_half_white_over_black_reads_half_within_one_step(ctx):
    r, size = _renderer(ctx), (8, 8)
    white = _solid(ctx, size, (255, 255, 255, 255))
    _, fbo = _target(ctx, size, (0, 0, 0, 255))
    assert r.mix_pass(fbo, (0, 0, *size), white, 0.5)
    px = _read(fbo, size)
    assert (np.abs(px[..., :3].astype(int) - 127.5) <= 1.0).all()
    assert (px[..., 3] == 255).all()              # an opaque ground stays opaque


def test_the_mix_is_linear_and_ends_on_the_other_decks_bytes(ctx):
    r, size = _renderer(ctx), (8, 8)
    src = np.random.default_rng(1).integers(0, 256, (size[1], size[0], 4), dtype=np.uint8)
    src[..., 3] = 255
    tex = ctx.texture(size, 4, src.tobytes())
    _, fbo = _target(ctx, size, (200, 10, 90, 255))
    assert r.mix_pass(fbo, (0, 0, *size), tex, 1.0)
    assert (_read(fbo, size) == src).all()
    _, fbo = _target(ctx, size, (200, 200, 200, 255))
    w = _solid(ctx, size, (100, 100, 100, 255))
    assert r.mix_pass(fbo, (0, 0, *size), w, 0.25)
    assert abs(int(_read(fbo, size)[0, 0, 0]) - 175) <= 1


def test_a_transparent_part_of_the_other_deck_shows_nothing_of_the_leaving_one_at_1(ctx):
    """See-through ground: colour and alpha mix, the leaving deck gone at 1."""
    r, size = _renderer(ctx), (4, 4)
    clear = _solid(ctx, size, (0, 0, 0, 0))
    _, fbo = _target(ctx, size, (200, 200, 200, 255))
    assert r.mix_pass(fbo, (0, 0, *size), clear, 1.0, opaque=False)
    assert (_read(fbo, size) == 0).all()


def test_a_mix_that_cannot_run_leaves_the_picture_and_says_so(ctx):
    """Findings of the review: a bad texture is refused before anything is
    multiplied; a raise in the add is said, never raised; a dim that will not
    build is named; a reload builds the program again and clears the word."""
    r, size = _renderer(ctx), (8, 8)
    white = _solid(ctx, size, (255, 255, 255, 255))
    _, fbo = _target(ctx, size, (200, 200, 200, 255))
    vp = (0, 0, *size)

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    assert not r.mix_pass(fbo, vp, SimpleNamespace(size=size, use=boom), 0.5)
    assert "boom" in r.mix_error
    assert (_read(fbo, size)[..., :3] == 200).all()      # the on-air picture as it was
    assert r.mix_pass(fbo, vp, white, 0.0) and r.mix_error == ""   # and it recovers
    vao, r._mix_vao = r._mix_vao, SimpleNamespace(render=boom)
    assert not r.mix_pass(fbo, vp, white, 0.5)
    assert "boom" in r.mix_error
    r._mix_vao = vao
    r._dim_prog, r.dim_error = None, "dim: refused"
    assert not r.mix_pass(fbo, vp, white, 0.5)
    assert "dim: refused" in r.mix_error
    r.on_reload()
    assert r._mix_prog is None and r.mix_error == "" and r.dim_error == ""
    assert r.mix_pass(fbo, vp, white, 1.0)
    assert (_read(fbo, size)[..., :3] == 255).all()


def test_the_mix_comes_before_the_dim(ctx):
    """`_compose`: a fade under a half-dim fades under a half-dim."""
    r, size = _renderer(ctx), (8, 8)
    white = _solid(ctx, size, (255, 255, 255, 255))
    pic = _solid(ctx, size, (0, 0, 0, 255))
    _, fbo = _target(ctx, size, (0, 0, 0, 255))
    v = View(Switches(dim=0.5), size, target=fbo, viewport=(0, 0, *size), mix=white, mix_k=1.0)
    r._compose(v, "k", False, {"k": pic}, set(), size)
    assert abs(int(_read(fbo, size)[0, 0, 0]) - 128) <= 1


def test_a_presenter_mixes_as_the_pass_does(ctx):
    """The hand-off's step 4½, in the presenter's context: the same bytes at 1,
    half at 0.5, and before the dim."""
    from hyperspace.outputs import Handoff, Presenter

    size = (8, 8)
    pres = Presenter(ctx)
    black = _solid(ctx, size, (0, 0, 0, 255))
    white = _solid(ctx, size, (255, 255, 255, 255))
    _, fbo = _target(ctx, size, (0, 0, 0, 255))
    ho = Handoff(black, size, (0, 0, *size), mix=white, mix_k=1.0)
    pres.present(ho, size, target=fbo)
    assert (_read(fbo, size)[..., :3] == 255).all()
    pres.present(Handoff(black, size, (0, 0, *size), mix=white, mix_k=0.5), size, target=fbo)
    assert (np.abs(_read(fbo, size)[..., :3].astype(int) - 127.5) <= 1).all()
    pres.present(Handoff(black, size, (0, 0, *size), mix=white, mix_k=1.0, factor=0.5), size,
                 target=fbo)
    assert abs(int(_read(fbo, size)[0, 0, 0]) - 128) <= 1


def _corpus_docs() -> list[Path]:
    return sorted((Path(__file__).parent / "corpus" / "presets").glob("*.json"))


@pytest.mark.empty_frame
@pytest.mark.parametrize("name", [p.stem for p in _corpus_docs()])
def test_deck_2_at_xfade_1_is_deck_1_on_the_same_loadable_byte_for_byte(ctx, tmp_path, name):
    """Plan 44 D4's proof: deck 2 loaded with loadable patch X, at `xfade` 1, draws
    exactly what deck 1 loaded with X draws at `xfade` 0 — through the fade's
    own road (`Fade.draw`, the mix pass), over a deck 1 on another look — and
    the on-air deck is not touched by deck 2 having drawn."""
    from hyperspace.render import Renderer

    size = (320, 200)
    home = tmp_path / "rig"
    rig = _gl_rig(ctx, home, Renderer)
    doc = json.loads((_corpus_dir() / f"{name}.json").read_text())

    # deck 1 on X, alone: the picture to match
    rig.a.loaded_patch.load_doc(doc, None)
    t = 7.0
    want = _frame(ctx, rig.a, size, t)
    assert want[..., :3].max() > 0, name         # the proof has teeth: a picture
    # deck 1 somewhere else; deck 2 on X
    other = "party-acid" if name != "party-acid" else "party-trip"
    rig.a.loaded_patch.load_doc(json.loads((_corpus_dir() / f"{other}.json").read_text()), None)
    rig.b.loaded_patch.load_doc(doc, None)
    alone = _frame(ctx, rig.a, size, t)
    assert not (alone == want).all(), name
    fade = Fade(rig.a, rig.b, Mix(xfade=1.0), ctx)
    got = _fade_frame(ctx, fade, size, t)
    assert (got == want).all(), name
    # the on-air deck after deck 2 drew: as it was
    assert (_frame(ctx, rig.a, size, t) == alone).all(), name
    fade.close()
    for d in (rig.a, rig.b):
        d.renderer.close()


def _corpus_dir() -> Path:
    return Path(__file__).parent / "corpus" / "presets"


def _gl_rig(ctx, home, renderer_cls):
    seeded = boot(home)
    lib, control, chain = seeded.lib, seeded.control, seeded.chain
    r1 = renderer_cls(ctx)
    r2 = r1.sibling()
    audio = SimpleNamespace(chain=chain, on=True)
    first = Deck.build(library=lib, control=control, audio=audio,
                       table=lambda reg: Bindings([]), renderer=r1,
                       attach=False, startup=False, install=False)
    second = Deck.beside(first, renderer=r2)
    return SimpleNamespace(a=first, b=second)


def _frame(ctx, deck, size, t):
    _tex, fbo = _target(ctx, size, (0, 0, 0, 255))
    fbo.use()
    ctx.viewport = (0, 0, *size)
    v = View(Switches(), size, target=fbo, viewport=(0, 0, *size))
    deck.renderer.draw_outputs(deck.view, *size, 1.0, [v], t_now=t)
    assert not v.error, v.error
    return _read(fbo, size)


def _fade_frame(ctx, fade, size, t):
    _tex, fbo = _target(ctx, size, (0, 0, 0, 255))
    fbo.use()
    ctx.viewport = (0, 0, *size)
    v = View(Switches(), size, target=fbo, viewport=(0, 0, *size))
    r2 = fade.off_air.renderer
    orig = r2.draw_outputs
    r2.draw_outputs = lambda s, w, h, dpr, views: orig(s, w, h, dpr, views, t_now=t)
    assert fade.draw([v], *size, 1.0)
    del r2.draw_outputs
    fbo.use()
    ctx.viewport = (0, 0, *size)
    fade.on_air.renderer.draw_outputs(fade.on_air.view, *size, 1.0, [v], t_now=t)
    assert not v.error, v.error
    return _read(fbo, size)


def _object_state(deck) -> dict:
    """What deck's renderer draws from: every patch param as its object
    holds it, and its states' own fields."""
    from dataclasses import asdict

    from hyperspace.params import part_of

    r = deck.renderer
    return {"params": {p.id: repr(p.get()) for p in deck.reg if part_of(p) == "patch"},
            "ghost": asdict(r.ghost.state), "dream": repr(asdict(r.lookback.state)),
            "view": repr(deck.view.pose())}


@pytest.mark.empty_frame
def test_deck_2_on_another_loadable_moves_nothing_of_the_on_air_deck(ctx, tmp_path):
    """Review finding 1: two different looks. Every corpus loadable patch landed on deck
    2, with its ghost, look-back and view values moved besides, leaves deck 1's
    params, its objects and, at xfade 0, its picture byte for byte. Only the
    room's mirror reaches both."""
    from hyperspace.render import Renderer

    rig = _gl_rig(ctx, tmp_path / "rig", Renderer)
    size = (160, 100)
    rig.a.loaded_patch.load_doc(json.loads((_corpus_dir() / "party-acid.json").read_text()), None)
    assert rig.a.renderer.ghost.state is not rig.b.renderer.ghost.state
    before, picture = _object_state(rig.a), _frame(ctx, rig.a, size, 2.0)
    for path in _corpus_docs():
        rig.b.loaded_patch.load_doc(json.loads(path.read_text()), None)
        for pid, v in (("ghost.alpha", 0.2), ("ghost.on", False), ("view.bright", 0.7)):
            rig.b.reg[pid].set(v)
        rig.b.reg.apply()
        assert _object_state(rig.a) == before, path.stem
    assert rig.b.renderer.ghost.state.alpha == 0.2
    assert (_frame(ctx, rig.a, size, 2.0) == picture).all()
    rig.a.reg["ghost.mirror"].set(True)
    assert rig.a.renderer.ghost.state.mirror and rig.b.renderer.ghost.state.mirror


def test_a_fade_after_the_rest_draws_again(ctx, tmp_path):
    from hyperspace.render import Renderer

    rig = _gl_rig(ctx, tmp_path / "rig", Renderer)
    size = (160, 100)
    doc = json.loads((_corpus_dir() / "party-acid.json").read_text())
    rig.b.loaded_patch.load_doc(doc, None)
    fade = Fade(rig.a, rig.b, Mix(xfade=1.0), ctx)
    first = _fade_frame(ctx, fade, size, 2.0)
    fade.mix.xfade = 0.0
    for _ in range(REST_FRAMES):
        fade.begin_frame()
    assert fade.targets == [] and rig.b.renderer.scene.tex is None
    fade.mix.xfade = 1.0
    assert (_fade_frame(ctx, fade, size, 2.0) == first).all()
    assert ctx.error == "GL_NO_ERROR"


def test_deck_2_draws_at_the_windows_sample_count(ctx, tmp_path):
    """A window has four samples, an offscreen target none: deck 2's scene
    takes the window's count, so the fade does not change the edges."""
    from hyperspace.render import Renderer

    rig = _gl_rig(ctx, tmp_path / "rig", Renderer)
    size = (160, 100)
    doc = json.loads((_corpus_dir() / "party-acid.json").read_text())
    rig.b.loaded_patch.load_doc(doc, None)
    fade = Fade(rig.a, rig.b, Mix(xfade=0.5), ctx)
    _tex, fbo = _target(ctx, size, (0, 0, 0, 255))
    v = View(Switches(), size, target=fbo, viewport=(0, 0, *size))
    assert fade.draw([v], *size, 1.0, samples=4), fade.error
    assert rig.b.renderer.scene.draw_fbo.samples == 4
    assert ctx.error == "GL_NO_ERROR"


def test_a_raise_in_a_real_deck_2_leaves_the_frame_the_on_air_decks(ctx, tmp_path):
    from hyperspace.render import Renderer

    rig = _gl_rig(ctx, tmp_path / "rig", Renderer)
    size = (160, 100)
    doc = json.loads(next(iter(_corpus_docs())).read_text())
    rig.a.loaded_patch.load_doc(doc, None)
    want = _frame(ctx, rig.a, size, 3.0)
    fade = Fade(rig.a, rig.b, Mix(xfade=0.7), ctx)

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    rig.b.renderer.draw_outputs = boom
    _tex, fbo = _target(ctx, size, (0, 0, 0, 255))
    v = View(Switches(), size, target=fbo, viewport=(0, 0, *size))
    assert not fade.draw([v], *size, 1.0)
    assert v.mix is None and "boom" in fade.error
    fbo.use()
    ctx.viewport = (0, 0, *size)
    rig.a.renderer.draw_outputs(rig.a.view, *size, 1.0, [v], t_now=3.0)
    assert (_read(fbo, size) == want).all()


# ----------------------------------------------------------- the frame's order

def test_the_frame_runs_the_off_air_deck_after_the_lead_and_its_raises_cost_nothing():
    from test_app_boundary import _host

    log: list[str] = []
    h = _host(log)
    calls: list[str] = []

    def boom(*_a):
        calls.append("off.modulate")
        raise RuntimeError("deck 2 is broken")

    real = h.router.modulate
    h.router.modulate = lambda *a: (calls.append("on.modulate"), real(*a))
    real_apply = h.reg.apply
    h.reg.apply = lambda: (calls.append("on.apply"), real_apply())
    h.off_air = [SimpleNamespace(
        router=SimpleNamespace(modulate=boom, follow_macros=lambda: calls.append("off.macros")),
        reg=SimpleNamespace(apply=lambda: calls.append("off.apply")),
        view=SimpleNamespace(integrate=lambda dt: calls.append("off.integrate")))]
    assert app.frame(h, now=1.0, dt=DT, fps=60.0) is False      # said, the frame goes on
    assert calls == ["off.macros", "on.modulate", "on.apply", "off.modulate", "off.integrate"]
    assert "deck 2 is broken" in h.reloader.runtime_error
    assert "render.draw" in log and "panel.draw" in log


def test_a_raise_in_one_close_leaves_the_others_to_close():
    """Second review pass: at quit or ⌘R a raise in deck 1's renderer close
    must not leave deck 2's segment workers alive, and `main` closes through
    this one road."""
    import inspect

    closed = []

    def boom():
        closed.append("deck 1")
        raise RuntimeError("boom")

    app._close_each([boom, lambda: closed.append("deck 2")])
    assert closed == ["deck 1", "deck 2"]
    src = inspect.getsource(app.main)
    assert "_close_each([r.close for r in rendering])" in src
    assert "[r.close() for r in rendering]" not in src


def test_main_builds_deck_2_beside_the_first_and_points_nothing_at_it():
    """The AST of `main`: one `Deck.beside`, its result handed only to the
    fade, the host's off-air list and the reloader, never to a device, a page
    or undo."""
    import ast
    import inspect

    src = inspect.getsource(app.main)
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "beside"]
    assert len(calls) == 1
    # (plan 44 D5a: and to the meta controller, which leaves every pointer on deck 1)
    assert src.count("deck2") == (src.count("deck2.router") + src.count("deck2.targets")
                                  + src.count("deck2.learn") + src.count("deck2.reg") + 3)
    assert "MetaController(deck, deck2, players, mix=mix)" in src
    assert "panel.deck = deck2" not in src and "undo.install(deck2" not in src
    assert ".point_panel(" not in src and "meta.point(" not in src     # nothing moves one
