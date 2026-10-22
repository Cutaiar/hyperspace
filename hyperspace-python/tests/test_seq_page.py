# ruff: noqa: F811 — `rig` is test_midi's fixture, taken as each test's argument
"""Plan 31 §A: the APC40's sequencer page, on the fake-port rig.

SEND A latches a surface page whose rows shadow clip rows 1–5, the clip
stops and scene launch 1–5 — invariant rows included — and are never
saved or learned. The sequencer is registered here by hand
(`sequencer.register`), as the app will once its wiring lands.
"""

import pytest
from test_midi import note, push, rig, shift  # noqa: F401 — the fixture

from hyperspace import apc40, learn, midi, routing, seq_page, sequencer, ui_desk
from hyperspace.routing import Binding, Bindings, bindings_path

CLIP, SCENE, STOP, SEND_A = apc40.N_CLIP, apc40.N_SCENE, apc40.N_CLIPSTOP, apc40.N_SEND_A


@pytest.fixture()
def seq(rig):
    s = sequencer.Sequencer()
    sequencer.register(rig.reg, s, rig.clock)
    return s


def tap(r, n, channel=0):
    push(r, note(n, channel=channel), note(n, 0, channel=channel))


def state(r, since=0) -> dict[tuple[int, int], int]:
    """Each note LED's last velocity in what was sent from `since` on."""
    return {(m.channel, m.note): m.velocity for m in r.out.sent[since:] if m.type == "note_on"}


def notes(r, since) -> list[tuple[int, int, int]]:
    return [(m.channel, m.note, m.velocity) for m in r.out.sent[since:] if m.type == "note_on"]


def enter(r):
    tap(r, SEND_A)
    assert seq_page.page_of(r.midi.table) is not None


def test_send_a_enters_and_the_grid_redraws_from_the_steps(rig, seq):
    seq.lanes[0].steps[2] = 1.0
    seq.lanes[3].steps[7] = 1.0
    was = state(rig)
    assert was[(0, CLIP[0])] != 0 or was[(4, CLIP[0])] != 0     # the bank is lit
    mark = len(rig.out.sent)
    enter(rig)
    got = state(rig, mark)
    assert got[(0, SEND_A)] == 1                               # SEND A lit while up
    for li in range(5):
        for si in range(8):
            want = apc40.GREEN if (li, si) in ((0, 2), (3, 7)) else 0
            assert got[(si, CLIP[li])] == want, (li, si)
    assert [got[(0, n)] for n in SCENE] == [1, 0, 0, 0, 0]       # lane 1 selected
    assert [got[(k, STOP)] for k in range(8)] == [0] * 8          # stopped: no playhead
    tap(rig, SEND_A)                                           # latched: again lets it go
    assert rig.midi.table.page is None and state(rig)[(0, SEND_A)] == 0


def test_send_a_does_nothing_until_the_sequencer_is_there(rig):
    tap(rig, SEND_A)
    assert rig.midi.table.page is None and not rig.reg["seq.page"].value


def test_a_pad_toggles_a_step_and_loads_no_preset(rig, seq):
    lib, pr = rig.presets.lib, rig.presets
    tap(rig, CLIP[0], channel=1)                               # off the page: slot 2 loads
    before, active = lib.current("presets"), pr.active
    enter(rig)
    mark = len(rig.out.sent)
    tap(rig, CLIP[0], channel=4)
    assert seq.lanes[0].steps[4] == 1.0
    assert (lib.current("presets"), pr.active) == (before, active)
    assert notes(rig, mark) == [(4, CLIP[0], apc40.GREEN)]     # only that pad changed
    tap(rig, CLIP[4], channel=0)                               # row 5 is a lane, not slots 17–24
    assert seq.lanes[4].steps[0] == 1.0 and pr.active == active
    tap(rig, CLIP[0], channel=4)
    assert seq.lanes[0].steps[4] == 0.0
    # a preset load (QUANT) leaves the page up, and the pattern with it
    tap(rig, apc40.N_QUANT)
    assert lib.current("presets") != before
    assert seq_page.page_of(rig.midi.table) is not None
    assert state(rig)[(0, CLIP[4])] == apc40.GREEN


def test_clip_stop_sets_the_length_and_clip_stop_8_does_not_save(rig, seq):
    seq.lanes[0].steps[5] = 1.0
    enter(rig)
    tap(rig, STOP, channel=2)
    assert seq.length == 3
    assert state(rig)[(5, CLIP[0])] == 0                       # past the length: dark…
    tap(rig, CLIP[0], channel=6)
    assert seq.lanes[0].steps[6] == 0.0                        # …and inert
    push(rig, note(STOP, channel=7))                           # SAVE's button, held
    assert not rig.reg[routing.SAVE_PARAM].value and seq.length == 8
    mark = len(rig.out.sent)
    tap(rig, CLIP[0], channel=1)                               # a pad while it is down: a step
    push(rig, note(STOP, 0, channel=7))
    assert seq.lanes[0].steps[1] == 1.0 and notes(rig, mark)[0] == (1, CLIP[0], apc40.GREEN)
    assert state(rig)[(5, CLIP[0])] == apc40.GREEN             # in the length again


def test_scene_1_selects_then_mutes_and_leaves_the_render_toggles(rig, seq):
    points = rig.reg["view.points"].value
    seq.lanes[0].steps[0] = 1.0
    enter(rig)
    tap(rig, SCENE[1])
    assert rig.reg[seq_page.SELECT_PARAM].value == 1 and not seq.lanes[1].mute
    tap(rig, SCENE[0])                                         # selects lane 1…
    assert rig.reg[seq_page.SELECT_PARAM].value == 0 and not seq.lanes[0].mute
    assert state(rig)[(0, SCENE[0])] == 1
    tap(rig, SCENE[0])                                         # …and again mutes it
    assert seq.lanes[0].mute and rig.reg[seq_page.SELECT_PARAM].value == 0
    got = state(rig)
    assert got[(0, SCENE[0])] == 2 and got[(0, CLIP[0])] == apc40.RED     # blink · red
    assert rig.reg["view.points"].value == points
    assert rig.midi.table.page.header() == "SEQ · lane 1 · L=8"
    tap(rig, SCENE[0])
    assert not seq.lanes[0].mute and state(rig)[(0, CLIP[0])] == apc40.GREEN


def test_an_advancing_playhead_sends_only_the_diff(rig, seq):
    for si in (0, 1, 2):
        seq.lanes[0].steps[si] = 1.0
    seq.lanes[2].steps[1] = 1.0
    seq.lanes[2].mute = True                                   # a muted step: no hit
    enter(rig)
    seq.playhead = 0
    push(rig)
    assert state(rig)[(0, CLIP[0])] == apc40.YELLOW and state(rig)[(0, STOP)] == 1
    mark = len(rig.out.sent)
    seq.playhead = 1
    push(rig)
    assert sorted(notes(rig, mark)) == sorted([
        (0, CLIP[0], apc40.GREEN), (1, CLIP[0], apc40.YELLOW),   # the lit steps
        (0, STOP, 0), (1, STOP, 1)])                              # the playhead's column
    mark = len(rig.out.sent)
    push(rig)
    assert notes(rig, mark) == []                              # nothing moved, nothing sent
    seq.playhead = 3                                           # an unlit column: the stop only
    push(rig)
    assert sorted(notes(rig, mark)) == sorted([(1, CLIP[0], apc40.GREEN), (1, STOP, 0),
                                              (3, STOP, 1)])


def test_leaving_restores_the_bank_the_toggles_and_save(rig, seq):
    lib = rig.presets.lib
    before = state(rig)
    enter(rig)
    tap(rig, CLIP[3], channel=2)
    tap(rig, SCENE[2])
    tap(rig, STOP, channel=4)
    tap(rig, SEND_A)
    assert rig.midi.table.page is None
    assert state(rig) == before                                # every light as it was
    push(rig, note(STOP, channel=7))                           # SAVE is back
    assert rig.reg[routing.SAVE_PARAM].value
    push(rig, note(STOP, 0, channel=7))
    tap(rig, CLIP[0], channel=0)                               # and the bank loads
    assert lib.current("presets") == rig.presets.bank[0]


def test_the_render_toggle_comes_back_on_leaving(rig, seq):
    p = rig.reg["view.points"]
    enter(rig)
    v = p.value
    tap(rig, SCENE[0])
    assert p.value == v
    tap(rig, SEND_A)
    tap(rig, SCENE[0])
    assert p.value != v


def test_a_bank_pad_held_across_send_a_never_saves(rig, seq):
    t = [0.0]
    rig.midi.clock = lambda: t[0]
    pr = rig.presets
    pr.clear_slot(5)
    push(rig, note(CLIP[0], channel=5))                        # the empty pad, held…
    push(rig, note(SEND_A), note(SEND_A, 0))                   # …across the switch
    t[0] = midi.HOLD_S + 0.1
    push(rig)
    assert pr.bank[5] is None
    push(rig, note(CLIP[0], 0, channel=5))                     # the release: nothing
    assert pr.bank[5] is None and seq.lanes[0].steps[5] == 0.0


def test_shift_inside_the_page_moves_the_knobs_not_the_grid(rig, seq):
    seq.lanes[1].steps[0] = 1.0
    enter(rig)
    grid = {k: v for k, v in state(rig).items() if k[1] in (*CLIP, *SCENE, STOP)}
    mark = len(rig.out.sent)
    shift(rig)
    assert rig.midi.table.layer == "global"
    assert any(m.type == "control_change" for m in rig.out.sent[mark:])   # the rings redrawn
    now = state(rig)
    assert {k: now[k] for k in grid} == grid
    scene = rig.reg["scene.select"].value
    tap(rig, CLIP[1], channel=0)                               # the band scenes' row: a step
    assert seq.lanes[1].steps[0] == 0.0 and rig.reg["scene.select"].value == scene


def test_learn_never_takes_a_page_control(rig, seq):
    enter(rig)
    m, table = rig.midi, rig.midi.table
    assert learn.blocked(table, f"note:3:{CLIP[2]}") == "invariant"
    m.learner.arm("view.lines")
    tap(rig, CLIP[2], channel=3)
    assert seq.lanes[2].steps[3] == 1.0                        # dispatched, not a candidate
    assert m.learner.learning == "view.lines"
    assert not [b for b in table.bindings if b.target == "view.lines" and b.kind == "note"
                and b.number == CLIP[2]]
    assert not [b for b in table.bindings if getattr(b, "shade", None)]   # never in the table
    assert "seq." not in table.dumps().replace("seq.page", "")                 # nor in the file


def test_a_power_cycle_with_the_page_up_resends_the_page(rig, seq):
    seq.lanes[0].steps[0] = 1.0
    enter(rig)
    mark = len(rig.out.sent)
    rig.midi._enter()
    got = state(rig, mark)
    assert got[(0, CLIP[0])] == apc40.GREEN and got[(0, SEND_A)] == 1


def test_older_files_get_send_a_unless_it_is_taken(tmp_path):
    session = [b for b in Bindings.factory().bindings
               if routing.is_session_row(b) and b.target != routing.SEQ_PAGE_PARAM]
    path = bindings_path(tmp_path / "a")
    (tmp_path / "a").mkdir()
    Bindings(session, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    assert [b.target for b in t.route("note", 0, SEND_A)] == [routing.SEQ_PAGE_PARAM]
    assert "added note:0:88 → seq.page (the APC40 map of plan 31)" in t.notes
    mine = Binding(f"note:0:{SEND_A}", "view.points", "toggle", feedback="led")
    path = bindings_path(tmp_path / "b")
    (tmp_path / "b").mkdir()
    Bindings([*session, mine], path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    assert [b.target for b in t.route("note", 0, SEND_A)] == ["view.points"]
    assert "the sequencer page not added: note:0:88 is yours (view.points)" in t.said
    assert routing.seq_missing(Bindings.factory().bindings) is None
    assert routing.seq_missing([]) is None


def test_the_on_screen_desk_shows_the_page(rig, seq):
    table = rig.midi.table
    assert ui_desk.lit(table)["G1·3"].target == "preset.select"
    seq.lanes[0].steps[2] = 1.0
    enter(rig)
    tap(rig, STOP, channel=3)                                  # L=4
    shown = ui_desk.lit(table)
    b = shown["G1·3"]
    assert b.target == "seq.1.3" and ui_desk.text(rig.reg, b) == "L1·3"
    assert routing.led_shade(b, rig.reg["seq.1.3"]) == "on"
    assert "G1·6" not in shown                                 # past the length: dark
    assert shown["G6·8"].target == "seq.length" and shown["G1·9"].target == "seq.1.mute"
    assert shown["G2·9"].target == seq_page.SELECT_PARAM
    c = next(c for c in apc40.LAYOUT if c.glyph == "G1·3")
    assert ui_desk.PAGE_OWNS in ui_desk.mappable(table, c)
    assert "sequencer page" in ui_desk.label(table, c, b, rig.reg)
    assert table.page.header() == "SEQ · lane 1 · L=4"
    tap(rig, SEND_A)
    assert ui_desk.lit(table)["G1·3"].target == "preset.select"
    assert ui_desk.mappable(table, c) is not None and ui_desk.PAGE_OWNS not in \
        ui_desk.mappable(table, c)
