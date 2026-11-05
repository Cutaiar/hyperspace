"""Plan 44 D5c: the crossfader and "copy on air to off air" (the owner, 2026-11-04).

Two fixed `Deck`s, a DJ mixer's crossfader, no swap: on air is whichever the
fader is closer to (`MetaController.follow_fader`). No caller in `app.main` but
the neutral wiring: deck 1 stays on air there until D5d. Headless first, over
`test_undo.boot`; then GL, with the `ctx` fixture.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from test_deck import _feed
from test_midi import cc
from test_undo import DT, boot

from hyperspace import app, lfo, poi, undo
from hyperspace.analyzer import CEIL
from hyperspace.deck import (
    MIDDLE,
    Deck,
    Fade,
    MetaController,
    Mix,
    draw_size,
)
from hyperspace.library import PRESETS
from hyperspace.outputs import Preview, Switches, View
from hyperspace.params import part_of
from hyperspace.pointer import Pointer
from hyperspace.routing import Binding, Bindings

CORPUS = Path(__file__).parent / "corpus" / "presets"


@pytest.fixture()
def rig(tmp_path):
    r = boot(tmp_path / "home")
    two = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    mix = r.mix
    meta = MetaController(r.deck, two, mix=mix)
    yield SimpleNamespace(r=r, meta=meta, one=r.deck, two=two, mix=mix, chain=r.chain)
    undo.install(None)


def _frame(rig) -> None:
    """One frame as `app.frame` runs it: the macros', the feeds, the lead's pass
    first, then the other's, then the integrators."""
    r, meta = rig.r, rig.meta
    r.t += DT
    r.clock.tick(r.t)
    _feed(r.router.sources, r.t)
    on, off = meta.on_air, meta.off_air
    for d in (on, off):
        d.router.follow_macros()
    for d in (on, off):
        d.undo.tick(r.t)
    for d in (on, off):
        d.router.modulate(rig.chain, DT, r.t)
        d.reg.apply()
    for d in (on, off):
        d.view.integrate(DT)


def _performance(deck) -> dict:
    """Every performance param as it lands, to the bit."""
    return {p.id: repr(p.value) for p in deck.reg
            if part_of(p) == "performance" and p.group != "ui"}


def _session(deck) -> dict:
    return {p.id: repr(p.value) for p in deck.session if p.group != "ui"}


def _diff(a: dict, b: dict) -> dict:
    return {k: (a.get(k), b.get(k)) for k in a.keys() | b.keys() if a.get(k) != b.get(k)}


# ------------------------------------------------------------- on air, by the fader

def test_at_0_exactly_today_and_on_air_is_the_side_the_fader_is_on(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    assert meta.on_air is one and meta.off_air is two and meta.parked == [two]
    assert one.session.lead is one.reg
    assert not meta.follow_fader()
    rig.mix.xfade = 0.5
    assert not meta.follow_fader() and meta.on_air is one
    rig.mix.xfade = 1.0
    assert meta.follow_fader()
    assert meta.on_air is two and meta.off_air is one and meta.parked == [one]
    assert one.session.lead is two.reg
    rig.mix.xfade = 0.0
    assert meta.follow_fader() and meta.on_air is one and one.session.lead is one.reg


def test_a_fader_sitting_at_the_middle_does_not_flap(rig):
    """7-bit jitter of a few steps about the middle, either way it arrived."""
    meta, one, two = rig.meta, rig.one, rig.two
    wobble = [0.5 + k / 127 for k in (-3, 3, -2, 2, 0, 1, -1)]
    assert all(abs(x - 0.5) < MIDDLE for x in wobble)
    for x in wobble:
        rig.mix.xfade = x
        assert not meta.follow_fader() and meta.on_air is one
    rig.mix.xfade = 0.5 + MIDDLE
    assert meta.follow_fader() and meta.on_air is two
    for x in wobble:
        rig.mix.xfade = x
        assert not meta.follow_fader() and meta.on_air is two


def _playered(rig):
    """A desk and pad on air (player 1), a pad off air (player 2)."""
    meta = rig.meta
    meta.register("edge", 2)
    meta.move_player(2, "off_air")
    return meta.pointer("apc40"), meta.pointer("edge")


def test_crossing_moves_on_air_once_and_each_player_with_its_duty(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    on, off = _playered(rig)
    keys, mouse = meta.pointer("window:keys"), meta.pointer("window:mouse")
    assert on.deck is one and off.deck is two
    moved = []
    meta.on_air_moved.append(moved.append)
    meta.point_panel(one)
    for x in np.linspace(0.0, 1.0, 200):
        rig.mix.xfade = float(x)
        meta.tick(rig.r.t, DT)
    assert moved == [two]                         # once
    assert on.deck is two                         # the performer stays on air
    assert off.deck is one                        # the other stays off air
    assert keys.deck is two and mouse.deck is two  # the picture's
    meta.pointers.pop("window:keys")               # asked for after the crossing: on air
    assert meta.pointer("window:keys").deck is two
    assert meta.panel is one                      # the panel is where it was put
    assert undo.installed() is one.undo
    assert meta.players.get(1).duty == "on_air" and meta.players.get(2).duty == "off_air"


def test_keys_pointed_elsewhere_go_to_the_picture_at_a_crossing(rig):
    meta, two = rig.meta, rig.two
    keys = meta.pointer("window:keys")
    meta.point("window:keys", two)                 # by hand, ahead of the fade
    rig.mix.xfade = 1.0
    meta.tick(rig.r.t, DT)
    assert keys.deck is two                        # never inverted off air


def test_a_held_chase_lets_go_on_the_deck_left_one_step_on_its_stack(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    one.chase(True)
    assert one.reg.chasing
    steps = len(one.undo.stack)
    rig.mix.xfade = 1.0
    meta.tick(rig.r.t, DT)
    assert not one.reg.chasing and meta.on_air is two
    assert one.undo._kept is None
    assert len(one.undo.stack) <= steps + 1


def test_no_session_param_jumps_at_the_middle(rig):
    """Same look or not: the session's values are one object, and a row of the
    session's reads on from the same follower."""
    meta, one, two = rig.meta, rig.one, rig.two
    one.reg["output.dim"].set(0.7)
    one.presets.load(min(one.presets.lib.list(PRESETS)))
    meta.copy_on_air()
    for _ in range(20):
        _frame(rig)
    was = _session(one)
    rig.mix.xfade = 1.0
    meta.tick(rig.r.t, DT)
    assert one.session.lead is two.reg
    for k in range(10):
        _frame(rig)
        moved = {i: v for i, v in _diff(was, _session(two)).items() if i != "output.xfade"}
        assert not moved, (k, moved)


def test_only_the_deck_on_air_lands_the_session_after_a_crossing(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    assert one.reg.lands(one.reg["output.dim"]) and not two.reg.lands(one.reg["output.dim"])
    rig.mix.xfade = 1.0
    meta.tick(rig.r.t, DT)
    assert two.reg.lands(one.reg["output.dim"]) and not one.reg.lands(one.reg["output.dim"])


def test_a_desk_fader_on_a_session_param_reads_on_across_the_middle(rig):
    """Over the MASTER's real row and fake ports: a crossing is a pointer's move, and
    the catch of a session fader stays (D5a's `MidiIO._follow_pointer`)."""
    meta, one, two = rig.meta, rig.one, rig.two
    midi = rig.r.midi
    midi.point(meta.pointer("apc40"), meta.panel_pointer)
    gain = one.reg["output.dim"]
    gain.set_norm(0.5)
    midi.poll()
    row = next(b for b in midi.table.bindings if b.source == "cc:0:14")
    at = round(gain.norm * 127)
    rig.r.inp.queue.extend([cc(14, at), cc(14, at + 1)])
    midi.poll()
    midi._land_all()
    assert row.caught is True
    was = gain.norm
    rig.mix.xfade = 1.0
    meta.tick(rig.r.t, DT)
    assert meta.pointer("apc40").deck is two and midi.reg is two.reg
    midi.poll()
    assert row.caught is True and gain.norm == was
    rig.r.inp.queue.append(cc(14, at + 3))
    midi.poll()
    midi._land_all()
    assert gain.norm > was


# ----------------------------------------------------------------- the timed fade

def test_a_timed_fade_runs_the_param_over_its_seconds_and_crosses_once(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    rig.one.reg["output.xfade_s"].set(1.0)
    writes = []
    p = one.reg["output.xfade"]
    real = p.set
    p.set = lambda v: (writes.append(v), real(v))
    moved = []
    meta.on_air_moved.append(moved.append)
    meta.crossfade()
    t = 50.0
    seen = []
    for _ in range(70):
        t += DT
        meta.tick(t, DT)
        seen.append(rig.mix.xfade)
    assert seen[0] == pytest.approx(DT)           # the first frame already moves
    assert seen[29] == pytest.approx(0.5, abs=DT)
    assert seen == sorted(seen) and seen[-1] == 1.0 and meta.timed is None
    assert writes and writes[-1] == 1.0
    assert moved == [two] and meta.on_air is two
    meta.crossfade()                              # and home, from the far end
    for _ in range(70):
        t += DT
        meta.tick(t, DT)
    assert rig.mix.xfade == 0.0 and meta.on_air is one


def test_0_seconds_cuts_at_the_next_tick(rig):
    meta, two = rig.meta, rig.two
    rig.one.reg["output.xfade_s"].set(0.0)
    meta.crossfade()
    assert rig.mix.xfade == 0.0 and meta.on_air is rig.one      # nothing until the frame
    meta.tick(10.0, DT)
    assert rig.mix.xfade == 1.0 and meta.on_air is two and meta.timed is None


def test_a_hand_on_the_fader_ends_a_timed_fade_there(rig):
    meta = rig.meta
    rig.one.reg["output.xfade_s"].set(2.0)
    meta.crossfade()
    meta.tick(10.0, DT)
    meta.tick(10.0 + DT, DT)
    rig.one.reg["output.xfade"].set(0.25)
    meta.tick(10.0 + 2 * DT, DT)
    assert meta.timed is None and rig.mix.xfade == 0.25
    meta.tick(11.0, DT)
    assert rig.mix.xfade == 0.25


# ----------------------------------------------------------------- copy, headless

@pytest.mark.parametrize("ran", [0, 45], ids=["just loaded", "running"])
def test_copy_then_every_performance_param_of_both_decks_equal_each_frame(rig, ran):
    """Over every corpus preset, whatever was on the deck off air: 120 frames,
    one lane vector, not a bit apart, and `signature` and the dirty dot agree."""
    meta, one, two = rig.meta, rig.one, rig.two
    names = sorted(one.presets.lib.list(PRESETS))
    assert len(names) > 5
    rig.chain.out = CEIL * np.linspace(0.15, 0.85, len(rig.chain.out))
    for name in names:
        one.presets.load(name)
        for _ in range(ran):
            _frame(rig)
        before = _performance(one)
        assert meta.copy_on_air() == [], name
        assert _performance(one) == before, name  # the source is not moved
        assert two.presets.current == one.presets.current, name
        assert two.presets.is_dirty() == one.presets.is_dirty(), name
        assert undo.alike(two.presets.signature(), one.presets.signature()), name
        assert two.presets.notes == [], (name, two.presets.notes)
        for k in range(120):
            _frame(rig)
            diff = _diff(_performance(one), _performance(two))
            assert not diff, (name, k, dict(list(diff.items())[:5]))
        assert list(two.view.ang) == list(one.view.ang), name
        assert two.view.inst_phase == one.view.inst_phase, name
        assert two.view.media_phase == one.view.media_phase, name


def test_a_copy_carries_the_pose_and_the_phases_not_the_doc_s_folded_ones(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    one.view.ang = [100.5, -7.25, 3.0, 0.25, 9.0, 0.5]
    one.view.inst_phase, one.view.media_phase = 1.25, 2.5
    meta.copy_on_air()
    assert two.view.ang == one.view.ang and two.view.ang is not one.view.ang
    assert two.view.inst_phase == 1.25 and two.view.media_phase == 2.5


def _chased(rig):
    """On air: a chase with a push still out on `view.bright`, a real route."""
    one = rig.one
    one.table.add(Binding("axis:LX", "view.bright", "push", 0.5))
    one.chase(True)
    for _ in range(20):
        _frame(rig)
    one.chase(False)
    for _ in range(3):
        _frame(rig)
    p = one.reg["view.bright"]
    assert p._trim, "the proof needs a push out"
    return p


def test_a_copy_after_a_chase_with_a_push_out_does_not_jump(rig):
    """`Registry.restore` with no trims empties the ledger (the reading's row 3):
    B would land base + whole push where A lands base + push − trim."""
    p = _chased(rig)
    q_id = p.id
    rig.meta.copy_on_air()
    q = rig.two.reg[q_id]
    assert q._trim == p._trim and q.base == p.base
    for k in range(30):
        _frame(rig)
        assert q.value == p.value, k


def test_a_copy_onto_a_deck_that_had_another_row_there_keeps_the_ledger(rig):
    """The doc road changes the deck's rows, and a rebuilt patch forgets a param
    whose rows are lost (plan 52): that must come before the ledger lands."""
    two = rig.two
    two.table.add(Binding("axis:RX", "view.bright", "push", 0.5))
    for _ in range(2):
        _frame(rig)
    p = _chased(rig)
    rig.meta.copy_on_air()
    q = two.reg[p.id]
    assert q._trim == p._trim
    for k in range(5):
        _frame(rig)
        assert q.value == p.value, k


def test_copy_leaves_the_mirror(rig):
    """`ghost.mirror` is the meta controller's in a performance group, one object
    on both, in no preset (`_values` is `snapshot(part="performance")`)."""
    meta, one, two = rig.meta, rig.one, rig.two
    mirror = one.reg["ghost.mirror"]
    assert two.reg["ghost.mirror"] is mirror and part_of(mirror) == "session"
    mirror.set(1)
    was = mirror.base
    doc = one.presets.document("x")
    assert "ghost.mirror" not in doc["values"]
    meta.copy_on_air()
    assert mirror.base == was


def test_a_copy_is_one_step_on_the_off_air_stack_and_its_undo_puts_the_look_back(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    names = sorted(one.presets.lib.list(PRESETS))
    two.presets.load(names[1])
    for _ in range(40):
        _frame(rig)
    two_look, two_name = two.reg.snapshot(part="performance"), two.presets.current
    two_routes = [b.to_json() for b in two.table.routes()]
    steps, one_steps = len(two.undo.stack), len(one.undo.stack)
    one.presets.load(names[0])
    for _ in range(40):
        _frame(rig)
    one_steps = len(one.undo.stack)
    meta.copy_on_air()
    for _ in range(90):
        _frame(rig)
    assert len(two.undo.stack) == steps + 1
    assert len(one.undo.stack) == one_steps
    assert two.undo.undo()
    assert two.presets.current == two_name
    assert [b.to_json() for b in two.table.routes()] == two_routes
    now = two.reg.snapshot(part="performance")
    assert undo.alike(now, two_look)


def test_copying_onto_an_empty_deck_leaves_no_undo_back_to_black(rig):
    meta, two = rig.meta, rig.two
    assert two.presets.current is None and not two.undo.stack
    meta.copy_on_air()
    for _ in range(90):
        _frame(rig)
    assert two.presets.current == rig.one.presets.current
    assert not two.undo.stack and two.undo._open is None
    assert not two.undo.undo()
    assert two.presets.current == rig.one.presets.current


def test_a_copy_of_unsaved_edits_is_dirty_and_a_clean_look_clean(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    meta.copy_on_air()
    assert not two.presets.is_dirty()
    one.reg["view.bright"].set(one.reg["view.bright"].value * 0.5)
    meta.copy_on_air()
    assert one.presets.is_dirty() and two.presets.is_dirty()
    one.presets.new()
    meta.copy_on_air()
    assert two.presets.unsaved and two.presets.is_dirty()


def test_nothing_of_a_copy_is_shared_after_it(rig):
    """No preset can affect another: a knob, a route, an LFO on the copy."""
    meta, one, two = rig.meta, rig.one, rig.two
    one.table.add(Binding("axis:LX", "view.bright", "push", 0.5))
    meta.copy_on_air()
    look = one.reg.snapshot(part="performance")
    rows = [b.to_json() for b in one.table.routes()]
    two.reg["view.bright"].set(0.1)
    two.table.remove(two.table.routes()[0])
    two.lfos.add()
    assert one.reg.snapshot(part="performance") == look
    assert [b.to_json() for b in one.table.routes()] == rows
    assert one.presets.current == two.presets.current


# ------------------------------------------------------------- neutrality, the wires

def test_main_moves_nothing_and_calls_no_verb():
    src = inspect.getsource(app.main)
    for verb in (".copy_on_air(", ".crossfade(", ".follow_fader(", "meta.tick(", ".place_players("):
        assert verb not in src, verb
    assert "off_air=meta.parked" in src
    assert "pointer=meta.on_air_pointer" in src
    assert "media.heard = lambda: meta.on_air.presets.media" in src


def test_the_frame_runs_the_deck_parked_list_it_is_handed(rig):
    """`Host.off_air` is the meta controller's own list, so it reads the crossing."""
    parked = rig.meta.parked
    assert parked == [rig.two]
    rig.mix.xfade = 1.0
    rig.meta.follow_fader()
    assert parked == [rig.one]


def test_the_mixer_plays_the_deck_on_air():
    log: list[tuple[str, bool]] = []
    src = SimpleNamespace(begin_frame=lambda: None)

    def chans(name):
        return SimpleNamespace(sources=src, drop_sources=lambda: None,
                               poll=lambda dt, now, heard: log.append((name, heard)))

    a, b = chans("a"), chans("b")
    io = app.MediaIO(SimpleNamespace(stop=lambda: None), a)
    io.off_air.append(b)
    io.poll(DT, 1.0)
    assert log == [("b", False), ("a", True)]     # nothing asks: the first; the silent one first
    log.clear()
    io.heard = lambda: b
    io.poll(DT, 1.0)
    assert log == [("a", False), ("b", True)]


def test_a_deck_leaving_the_air_lets_its_soundtrack_go_and_coming_back_asks_again():
    """Plan 45's roads over the move: the deck left does not decode on, and turning
    play-audio off on the other deck cannot strand it silent on return."""
    from test_media_mixer import rig as media_rig
    from test_media_mixer import track

    m, _, _ = media_rig("shared:a.mp4")
    ch = m.channels["a"]
    ch.play_audio = True
    m.poll(DT, 0.0)
    t = track(m, "a")
    assert (t.enables, t.disables) == (1, 0) and ch.heard is t
    m.poll(DT, 0.1, heard=False)
    assert ch.heard is None and m.drain(2.0)
    assert (t.enables, t.disables) == (1, 1)
    m.poll(DT, 0.2, heard=False)
    assert m.drain(2.0) and (t.enables, t.disables) == (1, 1)    # once
    m.poll(DT, 0.3)
    assert ch.heard is t and (t.enables, t.disables) == (2, 1)


def test_the_poi_guide_is_on_the_picture_of_the_deck_its_pad_is_on(rig):
    one, two = rig.one, rig.two
    state = poi.PoiState()
    state.on = True
    assert poi.guides(state, one.reg) and not poi.guides(state, two.reg)    # on air, no pad
    state.on_reg = two.reg
    assert poi.guides(state, two.reg) and not poi.guides(state, one.reg)
    state.on_reg = None
    rig.mix.xfade = 1.0
    rig.meta.follow_fader()
    assert poi.guides(state, two.reg) and not poi.guides(state, one.reg)
    assert poi.guides(state, None)                # a renderer with no deck behind it


def test_main_puts_the_rigs_wires_on_both_renderers():
    src = inspect.getsource(app.main)
    assert "renderer2.cloud_source, renderer2.poi_source = " in src
    assert "renderer2.ghost.source = renderer.ghost.source" in src
    assert "for r in rendering:" in src


# ------------------------------------------------- the lend over stand-ins

class _Dream:
    def __init__(self):
        self.lent = []

    def lend(self, reg):
        self.lent.append(reg)


def _fading(dreams=(True, True)):
    def deck(name, on):
        spec = SimpleNamespace(dream="node" if on else None)
        return SimpleNamespace(reg=f"reg {name}", graph=SimpleNamespace(spec=spec),
                               renderer=SimpleNamespace(
                                   dreamer=SimpleNamespace(source=None,
                                                           state=SimpleNamespace(on=True))))

    a, b = deck("a", dreams[0]), deck("b", dreams[1])
    dream = _Dream()
    mix = Mix()
    pointer = Pointer(a)
    a.renderer.dreamer.source = dream
    return SimpleNamespace(a=a, b=b, fade=Fade(a, b, mix, None, dream=dream, pointer=pointer),
                           mix=mix, pointer=pointer, dream=dream)


def test_the_lend_goes_once_across_a_whole_fade_and_is_not_restarted_at_the_middle():
    f = _fading()
    for x in np.linspace(0.0, 1.0, 101):
        f.mix.xfade = float(x)
        if x >= 0.5 + MIDDLE:
            f.pointer.deck = f.b
        f.fade.lend()
    assert f.dream.lent == ["reg b"]              # at LEND_AT, and never again
    assert f.fade.lent_to is f.b and f.fade.rest is f.b
    assert f.b.renderer.dreamer.source is f.dream and f.a.renderer.dreamer.source is None
    for x in np.linspace(1.0, 0.0, 101):          # and back the same way
        f.mix.xfade = float(x)
        if x <= 0.5 - MIDDLE:
            f.pointer.deck = f.a
        f.fade.lend()
    assert f.dream.lent == ["reg b", "reg a"]


def test_a_fade_back_short_of_the_far_end_returns_the_worker_once():
    f = _fading()
    for x in [*np.linspace(0.0, 0.7, 50), *np.linspace(0.7, 0.0, 50)]:
        f.mix.xfade = float(x)
        if x >= 0.5 + MIDDLE:
            f.pointer.deck = f.b
        elif x <= 0.5 - MIDDLE:
            f.pointer.deck = f.a
        f.fade.lend()
    assert f.dream.lent == ["reg b", "reg a"]


def test_a_deck_with_no_dream_coming_in_leaves_the_worker_until_the_end():
    f = _fading(dreams=(True, False))
    for x in np.linspace(0.0, 0.98, 50):
        f.mix.xfade = float(x)
        if x >= 0.5 + MIDDLE:
            f.pointer.deck = f.b
        f.fade.lend()
    assert f.dream.lent == []


def test_k_is_the_other_decks_share_and_0_at_either_end():
    f = _fading()
    f.mix.xfade = 0.25
    assert f.fade.k == 0.25
    f.pointer.deck = f.b
    assert f.fade.k == 0.75 and f.fade.on_air is f.b and f.fade.off_air is f.a
    f.mix.xfade = 1.0
    assert f.fade.k == 0.0


def _system(fade):
    from hyperspace.ui import Panel

    return Panel.deck2_gpu_lines(SimpleNamespace(fade=fade))


def test_system_names_the_deck_off_air_and_says_when_the_backdrop_draws_it():
    f = _fading()
    f.a.renderer.mix_error = f.b.renderer.mix_error = ""
    f.b.renderer.stats = f.a.renderer.stats = {"gpu_ms": {"scene": 1.5}, "ends": ["shown(scene)"]}
    assert _system(f.fade) == ["deck 2: off air, draws nothing"]
    f.fade.previewed = True
    assert _system(f.fade)[0].startswith("deck 2 gpu")
    f.fade.previewed = False
    f.pointer.deck = f.b
    assert _system(f.fade) == ["deck 1: off air, draws nothing"]
    f.fade.warm_error = "warm draw: no"
    assert _system(f.fade)[-1] == "deck 1: warm draw: no"


class _Tgt:
    def __init__(self, ctx=None):
        self.tex = object()
        self.released = False

    def fit(self, size):
        return self

    def release(self):
        self.released = True


def _warming(dreams=(False, False)):
    f = _fading(dreams)
    f.fade.make_target = _Tgt
    log = []
    for d, name in ((f.a, "a"), (f.b, "b")):
        d.view = name
        r = d.renderer
        r.reset_delays = lambda name=name: log.append(f"reset {name}")
        r.release_sized = lambda: None
        r.draw_outputs = lambda s, w, h, dpr, views: log.append(f"draw {s}")
    f.log = log
    return f


def _land(deck):
    deck.graph.spec = SimpleNamespace(dream=None)


def test_a_save_lands_no_new_graph_so_it_asks_for_no_warm_draw():
    f = _warming()
    f.fade.ask_warm(f.b)
    assert f.fade.warm_deck is None               # told, nothing new
    _land(f.b)
    f.fade.ask_warm(f.b)
    assert f.fade.warm_deck is f.b
    assert f.fade.warm(8, 8, 1.0, Switches())
    f.log.clear()
    f.fade.ask_warm(f.b)                          # the save
    assert f.fade.warm_deck is None
    assert not f.fade.warm(8, 8, 1.0, Switches()) and f.log == []


def test_a_real_save_on_the_deck_off_air_keeps_its_spec(rig):
    two = rig.two
    two.presets.load(min(two.presets.lib.list(PRESETS)))
    spec = two.graph.spec
    two.presets.save_as("a save")
    assert two.graph.spec is spec


def test_a_warm_asked_during_a_fade_or_for_a_deck_gone_on_air_draws_nothing():
    f = _warming()
    f.mix.xfade = 0.2
    _land(f.b)
    f.fade.ask_warm(f.b)
    assert not f.fade.warm(8, 8, 1.0, Switches())  # drawn by the fade anyway, and forgotten
    assert f.fade.warm_deck is None
    f.mix.xfade = 1.0
    f.pointer.deck = f.b
    assert not f.fade.warm(8, 8, 1.0, Switches()) and f.log == []
    f = _warming()
    _land(f.b)
    f.fade.ask_warm(f.b)
    f.mix.xfade = 1.0                              # a cut before the frame
    f.pointer.deck = f.b
    assert not f.fade.warm(8, 8, 1.0, Switches()) and f.log == []  # deck 1's trails stand


def test_a_failed_warm_draw_is_said_and_outlasts_the_frames_at_0():
    f = _warming()
    said = []
    f.fade.said = said.append

    def boom(*a):
        raise RuntimeError("no compile")

    f.b.renderer.draw_outputs = boom
    _land(f.b)
    f.fade.ask_warm(f.b)
    assert not f.fade.warm(8, 8, 1.0, Switches())
    assert "no compile" in said[0]
    f.fade.lend = lambda: None
    for _ in range(5):
        f.fade.begin_frame()
    assert "no compile" in f.fade.warm_error
    f.b.renderer.draw_outputs = lambda *a: None
    _land(f.b)
    f.fade.ask_warm(f.b)
    assert f.fade.warm(8, 8, 1.0, Switches()) and f.fade.warm_error == ""


def test_the_backdrop_never_keeps_a_fades_texture_that_failed_or_went():
    f = _warming()
    f.fade.begin_frame = lambda: None
    pv = SimpleNamespace(tap=None, tex="last", publish=lambda tex, t: setattr(pv, "tex", tex))
    tgt = _Tgt()
    f.fade.targets, f.fade.drew, f.fade.first_ok = [tgt], True, False
    assert not f.fade.preview(pv, 8, 8, 1.0, (8, 8), Switches())   # a frame that failed
    assert pv.tex == "last"
    f.fade.first_ok = True
    assert f.fade.preview(pv, 8, 8, 1.0, (8, 8), Switches())
    assert pv.tex is tgt.tex
    f.fade.close()
    assert pv.tex is None and tgt.released


# ----------------------------------------------------------------- GL

def _docs() -> list[Path]:
    return sorted(CORPUS.glob("*.json"))


def _gl(ctx, home):
    from hyperspace.render import Renderer

    seeded = boot(home)
    r1 = Renderer(ctx)
    r2 = r1.sibling()
    audio = SimpleNamespace(chain=seeded.chain, on=True)
    first = Deck.build(library=seeded.lib, control=seeded.control, audio=audio,
                       table=lambda reg: Bindings([]), renderer=r1,
                       attach=False, startup=False, install=False)
    second = Deck.beside(first, renderer=r2)
    mix = Mix()
    meta = MetaController(first, second, mix=mix)
    fade = Fade(first, second, mix, ctx, pointer=meta.on_air_pointer)
    for d in meta.decks:                          # as `app.main`
        d.presets.listeners.append(lambda name, d=d: fade.ask_warm(d))
    return SimpleNamespace(a=first, b=second, meta=meta, fade=fade, mix=mix)


def _target(ctx, size):
    tex = ctx.texture(size, 4)
    return tex, ctx.framebuffer([tex])


def _read(fbo, size):
    return np.frombuffer(fbo.read(components=4), np.uint8).reshape(size[1], size[0], 4).copy()


def _draw(ctx, rig, size, t):
    """Output 1 as `_draw_render` draws it, through the fade: at the on-air deck's
    end of the fader, that deck alone."""
    _tex, fbo = _target(ctx, size)
    fbo.use()
    ctx.viewport = (0, 0, *size)
    v = View(Switches(), size, target=fbo, viewport=(0, 0, *size))
    fade = rig.fade
    fade.begin_frame()
    if fade.k > 0.0:
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


def _feeds_back(doc) -> bool:
    text = json.dumps(doc["graph"]["wires"])
    return any(w in text for w in ("delay", "lookback", "dream"))


@pytest.mark.empty_frame
@pytest.mark.parametrize("name", [p.stem for p in _docs()])
def test_copy_then_xfade_1_is_deck_1_at_0(ctx, tmp_path, name):
    """Copy, then the fader at the far end draws what deck 1 draws at the near one:
    byte for byte on a look with no feedback, close on one with (a load's trails
    start empty). The proof's frames are one frame of one `t`, as the D4 one's."""
    size = (320, 200)
    rig = _gl(ctx, tmp_path / "rig")
    doc = json.loads((CORPUS / f"{name}.json").read_text())
    rig.a.presets.load_doc(doc, None)
    t = 7.0
    for _ in range(3):                           # running: its clocks and turn off their zeros
        rig.a.view.integrate(0.25)
        _draw(ctx, rig, size, t)
        t += DT
    rig.meta.copy_on_air()
    want = _draw(ctx, rig, size, t)
    assert want[..., :3].max() > 0, name
    rig.mix.xfade = 1.0
    rig.meta.tick(t, DT)
    assert rig.meta.on_air is rig.b and rig.fade.k == 0.0
    got = _draw(ctx, rig, size, t)
    if _feeds_back(doc):
        assert np.abs(got.astype(int) - want.astype(int)).mean() < 8.0, name
    else:
        assert (got == want).all(), name
    # and home: deck 1 at 0 again, by the same bytes
    rig.mix.xfade = 0.0
    rig.meta.tick(t, DT)
    assert rig.meta.on_air is rig.a
    if not _feeds_back(doc):
        assert (_draw(ctx, rig, size, t) == want).all(), name
    rig.fade.close()
    for d in (rig.a, rig.b):
        d.renderer.close()


@pytest.mark.empty_frame
def test_the_mix_either_side_of_the_middle_is_one_picture(ctx, tmp_path):
    """A 0.5 from deck 1's side and from deck 2's: the fader moving on air shows
    nothing, within a step or two."""
    size = (320, 200)
    rig = _gl(ctx, tmp_path / "rig")
    rig.a.presets.load_doc(json.loads((CORPUS / "party-acid.json").read_text()), None)
    rig.b.presets.load_doc(json.loads((CORPUS / "party-trip.json").read_text()), None)
    t = 7.0
    rig.mix.xfade = 0.5
    a_side = _draw(ctx, rig, size, t)
    rig.meta.on_air_pointer.deck = rig.b          # (past the middle, by hand)
    b_side = _draw(ctx, rig, size, t)
    assert np.abs(a_side.astype(int) - b_side.astype(int)).max() <= 2
    rig.fade.close()
    for d in (rig.a, rig.b):
        d.renderer.close()


@pytest.mark.empty_frame
def test_the_preview_road_draws_at_the_preview_size_and_reuses_a_fades_frame(ctx, tmp_path):
    size = (1600, 900)
    rig = _gl(ctx, tmp_path / "rig")
    doc = json.loads((CORPUS / "party-acid.json").read_text())
    rig.b.presets.load_doc(doc, None)
    pv = Preview(ctx)
    r = rig.b.renderer
    turns = []
    real = r.draw_outputs
    r.draw_outputs = lambda s, w, h, dpr, views, **kw: (turns.append(views[0].size),
                                                        real(s, w, h, dpr, views, **kw))[1]
    assert rig.fade.preview(pv, 800, 450, 2.0, size, Switches())
    assert turns == [draw_size(size, None, False)] == [(1280, 720)]
    assert pv.tex is pv.tap.tex and pv.status == "sending"
    # in a fade the deck has drawn this frame: its picture, and no second draw
    rig.mix.xfade = 0.5
    turns.clear()
    v = View(Switches(), size, target=_target(ctx, size)[1], viewport=(0, 0, *size))
    assert rig.fade.draw([v], 800, 450, 2.0)
    assert len(turns) == 1
    assert rig.fade.preview(pv, 800, 450, 2.0, size, Switches())
    assert len(turns) == 1 and pv.tex is rig.fade.targets[0].tex
    del r.draw_outputs
    pv.close()
    rig.fade.close()
    for d in (rig.a, rig.b):
        d.renderer.close()


@pytest.mark.empty_frame
@pytest.mark.parametrize("name", ["party-trip", "party-tracer", "party-wake"])
def test_a_warm_draw_compiles_now_and_leaves_the_picture_as_it_was(ctx, tmp_path, name):
    """After a warm draw the first full-size frame is the frame a deck with no warm
    draw makes, feedback looks included: nothing of the small frame stays in a trail."""
    size = (320, 200)
    doc = json.loads((CORPUS / f"{name}.json").read_text())
    t = 7.0
    cold = _gl(ctx, tmp_path / "cold")
    cold.b.presets.load_doc(doc, None)
    cold.mix.xfade = 1.0
    cold.meta.tick(t, DT)
    want = _draw(ctx, cold, size, t)

    warm = _gl(ctx, tmp_path / "warm")
    warm.b.presets.load_doc(doc, None)
    assert warm.fade.warm_deck is None           # `load_doc` alone tells no listener
    warm.fade.ask_warm(warm.b)
    warm.fade.ask_warm(warm.a)                   # (on air: drawn anyway, no matter)
    r2, orig = warm.b.renderer, warm.b.renderer.draw_outputs
    r2.draw_outputs = lambda s, w, h, dpr, views: orig(s, w, h, dpr, views, t_now=t)
    assert warm.fade.warm(*size, 1.0, Switches())
    del r2.draw_outputs
    assert warm.fade.warm_deck is None and not warm.fade.warm_error
    assert not warm.fade.warm(*size, 1.0, Switches())    # once
    warm.mix.xfade = 1.0
    warm.meta.tick(t, DT)
    got = _draw(ctx, warm, size, t)
    assert (got == want).all(), name
    for rig in (cold, warm):
        rig.fade.close()
        for d in (rig.a, rig.b):
            d.renderer.close()
