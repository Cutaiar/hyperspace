# ruff: noqa: F811 — `rig` is test_midi's fixture, taken as each test's argument
"""Plan 24 C1 — the desk you can trust (decisions 18 and 23).

Driven through `MidiIO` with the fake ports tests/test_midi.py injects (its
rig is reused: a scratch library whose show is the factory party show):

- **the two-handed save**: track 8's clip stop is SAVE (invariant); SAVE
  held and a bank pad tapped saves the live state into that pad's slot —
  an empty slot as #158's hold does, a filled slot as a **new** preset the
  slot then points at, the old preset's file untouched and still listed,
  the trash untouched; the pad blinks; SAVE alone does nothing; the same
  under SHIFT; ten times in a row;
- **every load relights the whole desk**: every ring and LED re-sent, every
  control nothing draws sent dark, and every fader the new preset binds
  picks up again (register row 44, changed);
- **the render toggles on both layers**: points, lines, faces and rotate
  are invariant rows whose LEDs show the live state; an older preset's
  toggle rows drop quietly at load (fixture under tests/fixtures/);
- **the desk event log**: the last twenty presses, what each did and on
  which layer.
"""

import json
import shutil
from pathlib import Path

import pytest
from test_midi import cc, leds, note, push, rig, shift  # noqa: F401 — the fixture

from hyperspace import apc40, midi, routing
from hyperspace.routing import SAVE_PARAM, Binding, Bindings, bindings_path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "desk-trust"
STOP = apc40.N_CLIPSTOP
SAVE_CH = 7                                   # track 8's clip stop
TOGGLES = (("view.points", apc40.N_SCENE[0]), ("view.lines", apc40.N_SCENE[1]),
           ("view.faces", apc40.N_SCENE[2]), ("view.rotate", apc40.N_SCENE[3]))


def clocked(rig):
    """The rig with a clock the test moves: `at(seconds, *msgs)`."""
    t = [0.0]
    rig.midi.clock = lambda: t[0]

    def at(seconds, *msgs):
        t[0] = seconds
        push(rig, *msgs)
    return at


def pad(k):
    """The (note, channel) of bank slot k's pad."""
    return apc40.BANK_PADS[k]


def tap(k):
    n, ch = pad(k)
    return note(n, channel=ch), note(n, 0, channel=ch)


def save_down():
    return note(STOP, channel=SAVE_CH)


def save_up():
    return note(STOP, 0, channel=SAVE_CH)


def user_files(lib) -> dict[str, bytes]:
    folder = lib.home / "presets"
    return {p.name: p.read_bytes() for p in folder.glob("*.json")} if folder.is_dir() else {}


def trash(lib) -> list[str]:
    folder = lib.home / "trash"
    return sorted(str(p.relative_to(folder)) for p in folder.rglob("*")) if folder.is_dir() \
        else []


# ------------------------------------------------------------- the SAVE button

def test_the_save_button_is_track_eights_clip_stop_invariant_and_lit_while_held(rig):
    """The owner's choice (2026-10-14): SAVE is track 8's clip stop, free
    since PR #158 — one invariant row, a momentary on `desk.save`, the same
    on both layers, its LED lit while it is held. A SAVE press with no pad
    does nothing: no file, no load, no slot moved. The other seven
    clip-stop buttons stay free for Learn."""
    t, lib, pr = rig.midi.table, rig.presets.lib, rig.presets
    (b,) = t.route("note", SAVE_CH, STOP)
    assert (b.target, b.op, b.layer, b.feedback) == (SAVE_PARAM, "momentary", None, "led")
    assert apc40.SAVE == (STOP, SAVE_CH) and apc40.glyph(b.source) == "G6·8"
    assert t.is_invariant(Binding(b.source, "view.speed", "toggle", layer="preset"))
    for k in range(7):
        assert t.route("note", k, STOP) == []
    save = rig.reg[SAVE_PARAM]
    assert not save.persist and not save.modulatable
    files, bank, cur = user_files(lib), list(pr.bank), lib.current("presets")
    for under_shift in (False, True):
        if under_shift:
            shift(rig)
        push(rig, save_down())
        assert save.value is True and leds(rig, STOP, SAVE_CH)[-1] == 1
        push(rig, save_up())
        assert save.value is False and leds(rig, STOP, SAVE_CH)[-1] == 0
    assert user_files(lib) == files and pr.bank == bank and lib.current("presets") == cur


def test_a_reconnect_lets_go_of_a_save_whose_release_was_lost(rig):
    """A SAVE whose note-off never came (the cable pulled while it was
    down) must not turn the next pad press into a save: power-up lets go."""
    push(rig, save_down())
    assert rig.reg[SAVE_PARAM].value is True
    rig.midi._enter()
    assert rig.reg[SAVE_PARAM].value is False
    push(rig, *tap(0))
    assert rig.presets.lib.current("presets") == "TUMBLE"


def test_nothing_can_latch_save(rig, tmp_path):
    """Review of PR #175: only a `momentary` row may drive `desk.save`. A
    learn onto it is refused (the desk, the pad), the table refuses a
    latching row at runtime, a preset's desk row that would latch it drops
    with a note, and a hand-edited bindings.json loses such a row with a
    note — never a crash, never SAVE stuck on."""
    from hyperspace.learn import SAVE_REFUSAL

    t, m = rig.midi.table, rig.midi
    rows = [b.to_json() for b in t.bindings]
    m.learner.arm(SAVE_PARAM, "desk")
    assert not m.learner.learn_control(f"note:0:{apc40.N_SCENE[4]}", apc40)
    assert m.learner.refused and m.learner.last == SAVE_REFUSAL
    m.learner.arm(SAVE_PARAM, "pad")
    assert not m.learner.learn_pad_button("pad:A")
    assert m.learner.last == SAVE_REFUSAL
    m.learner.arm(None)
    assert [b.to_json() for b in t.bindings] == rows
    for bad in (Binding("key:S", SAVE_PARAM, "toggle"),
                Binding(f"note:0:{apc40.N_SCENE[4]}", SAVE_PARAM, "toggle", layer="preset")):
        with pytest.raises(ValueError, match="momentary"):
            t.bind(bad)
        with pytest.raises(ValueError, match="momentary"):
            t.add(bad)
    assert [b.to_json() for b in t.bindings] == rows
    notes = t.set_desk([*t.desk(), {"source": f"note:0:{apc40.N_SCENE[4]}",
                                     "target": SAVE_PARAM, "op": "toggle"}])
    assert notes == [(f"dropped note:0:{apc40.N_SCENE[4]} → desk.save (toggle): desk.save "
                      "takes only a momentary row (held, never latched)")]
    # a hand-edited bindings.json
    path = bindings_path(tmp_path / "h")
    (tmp_path / "h").mkdir()
    session = [b for b in Bindings.factory().bindings if routing.is_session_row(b)]
    Bindings([*session, Binding("key:S", SAVE_PARAM, "toggle")], path=path).write()
    loaded = Bindings.load(path, legacy_midi=None)
    assert "dropped key:S → desk.save (toggle): desk.save takes only a momentary row " \
           "(held, never latched)" in loaded.notes
    assert [b.op for b in loaded.bindings if b.target == SAVE_PARAM] == ["momentary"]
    assert "\"key:S\"" not in path.read_text()                     # written back once


def test_save_not_added_is_said(tmp_path):
    """Review of PR #175: a bindings.json whose owner put a row on track 8's
    clip stop keeps it, and SAVE is not added there (`APC_NEW_ROWS` only
    takes a free control) — said on the SYSTEM page line (`said`) and on
    stderr at every launch, never silent."""
    session = [b for b in Bindings.factory().bindings
               if routing.is_session_row(b) and b.target != SAVE_PARAM]
    mine = Binding(f"note:{SAVE_CH}:{STOP}", "view.points", "toggle", feedback="led")
    path = bindings_path(tmp_path / "a")
    (tmp_path / "a").mkdir()
    Bindings([*session, mine], path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    assert [b.target for b in t.route("note", SAVE_CH, STOP)] == ["view.points"]
    assert "SAVE not added: note:7:52 is yours (view.points)" in t.said
    assert routing.save_missing(Bindings.factory().bindings) is None
    assert routing.save_missing([]) is None


def test_a_reconnect_forgets_where_the_faders_were(rig):
    """Review of PR #175: a fader moved while the cable was out must not
    seed a false pickup crossing — power-up forgets every position."""
    push(rig, cc(apc40.CC_FADER, 40, channel=2))
    assert rig.midi._hw
    rig.midi._enter()
    assert rig.midi._hw == {}


# --------------------------------------------------------- the two-handed save

def test_save_held_and_an_empty_pad_tapped_saves_into_that_slot(rig):
    """On an empty pad the two-handed save is #158's save: a new preset
    named from the loaded one into that slot, loaded, the pad blinking."""
    at = clocked(rig)
    lib, pr = rig.presets.lib, rig.presets
    at(0.0, *tap(4))                                                  # TRIP, on F5
    assert lib.current("presets") == "TRIP" and pr.bank[12] is None
    at(1.0, save_down())
    mark = len(rig.out.sent)
    n, ch = pad(12)
    at(1.1, note(n, channel=ch))
    assert pr.bank[12] == "TRIP 2" and lib.current("presets") == "TRIP 2" and pr.active == 12
    assert leds(rig, n, ch, mark) == [apc40.GREEN_BLINK]              # blinks at once
    at(1.2, note(n, 0, channel=ch), save_up())
    at(1.1 + midi.BLINK_S)
    assert leds(rig, n, ch, mark)[-1] == apc40.GREEN                   # then the loaded green
    assert lib.status == "saved TRIP 2 → slot 13"


def test_save_held_and_a_filled_pad_tapped_saves_a_new_preset_and_keeps_the_old(rig):
    """Decision 18: a filled slot takes a **new** preset (named as
    `save_new` names them) and the slot points at it; the old preset keeps
    its file, byte for byte, and stays in the list, unpadded, as "free
    this pad (keeps the preset)" leaves it; nothing goes to the trash; the
    new preset is the loaded one and its pad blinks."""
    at = clocked(rig)
    lib, pr = rig.presets.lib, rig.presets
    at(0.0, *tap(4))                                                  # TRIP
    at(0.5, save_down(), *tap(10), save_up())                         # TRIP 2 → slot 11
    assert pr.bank[10] == "TRIP 2"
    old = dict(user_files(lib))
    assert list(old) == ["trip-2.json"]
    gone = trash(lib)
    # the filled pad: slot 11, which holds TRIP 2 (a user preset) — and F3,
    # which holds FIELD (a factory one)
    at(5.0, save_down())
    mark = len(rig.out.sent)
    n, ch = pad(10)
    at(5.1, note(n, channel=ch), note(n, 0, channel=ch))
    assert pr.bank[10] == "TRIP 3" and lib.current("presets") == "TRIP 3" and pr.active == 10
    assert apc40.GREEN_BLINK in leds(rig, n, ch, mark)
    assert user_files(lib)["trip-2.json"] == old["trip-2.json"]       # untouched
    assert "TRIP 2" in lib.list("presets") and "TRIP 2" not in pr.bank   # listed, unpadded
    assert trash(lib) == gone
    assert lib.status == "saved TRIP 3 → slot 11 (TRIP 2 is still in the preset list)"
    fac = lib.path_of("presets", "FIELD")
    before = fac.read_bytes()
    at(5.5, *tap(2), save_up())
    assert pr.bank[2] == "TRIP 4" and "FIELD" in lib.list("presets") and fac.read_bytes() == before
    assert "FIELD" not in pr.bank and trash(lib) == gone
    # the show on disk says so
    show = json.loads(pr.path.read_text())
    assert show["bank"][2] == "TRIP 4" and show["bank"][10] == "TRIP 3"


def test_the_two_handed_save_works_ten_times_in_a_row(rig):
    """The acceptance (hand check U.1 at the desk): ten saves in a row,
    into empty and filled slots, SHIFT up and down — every one a new file,
    its slot pointing at it, loaded, its pad blinking, every earlier file
    untouched, the trash untouched, the layer left as it was."""
    at = clocked(rig)
    lib, pr, t = rig.presets.lib, rig.presets, rig.midi.table
    at(0.0, *tap(4))                                                  # TRIP
    gone = trash(lib)
    slots = [12, 0, 13, 12, 3, 20, 20, 8, 1, 23]       # empty, filled, …, the same one again
    clock = 1.0
    for i, k in enumerate(slots):
        if (t.layer == "global") != (i % 2 == 1):
            shift(rig)                                                # odd saves under SHIFT
        layer = t.layer
        before = user_files(lib)
        filled = pr.bank[k]
        at(clock, save_down())
        mark = len(rig.out.sent)
        n, ch = pad(k)
        at(clock + 0.1, note(n, channel=ch))
        new = f"TRIP {i + 2}"
        assert pr.bank[k] == new and lib.current("presets") == new and pr.active == k, i
        assert leds(rig, n, ch, mark)[0] == apc40.GREEN_BLINK, i
        now = user_files(lib)
        assert set(now) == {*before, f"trip-{i + 2}.json"}, i
        assert all(now[f] == before[f] for f in before), i            # nothing overwritten
        if filled is not None:
            assert filled in lib.list("presets"), i                    # the old one listed
        at(clock + 0.2, note(n, 0, channel=ch), save_up())
        assert t.layer == layer, i                                    # a save is not a load
        clock += 3.0
    assert trash(lib) == gone
    assert len(user_files(lib)) == 10


def test_a_save_tap_does_not_load_or_start_a_hold(rig):
    """The pad under SAVE is the save's and nothing else: its slot is not
    loaded first, and its hold (#158's save into an empty slot) never fires
    after it — one press, one preset."""
    at = clocked(rig)
    lib, pr = rig.presets.lib, rig.presets
    at(0.0, *tap(4))
    loads = []
    pr.lib.on_load("presets", loads.append)       # (a save lands the new preset too)
    at(1.0, save_down())
    for k in (1, 15):                             # a filled pad (FACES), an empty one
        n, ch = pad(k)
        at(1.1, note(n, channel=ch))
        assert rig.midi._hold_state()[0] == {}                        # no hold started
        at(1.1 + 2 * midi.HOLD_S)                                     # held well past it
        at(3.0, note(n, 0, channel=ch))
    at(3.1, save_up())
    assert pr.bank[1] == "TRIP 2" and pr.bank[15] == "TRIP 3"
    assert "FACES" not in loads                                       # never loaded first
    assert len(user_files(lib)) == 2


def test_a_failed_save_into_a_filled_slot_leaves_the_slot_and_blinks_nothing(rig, monkeypatch):
    """A show file that cannot be written keeps the slot on the preset it
    named (the new preset is saved and in the list, the footer says why);
    a save that could not be written at all blinks nothing."""
    at = clocked(rig)
    lib, pr = rig.presets.lib, rig.presets
    at(0.0, *tap(4))

    def refuse():
        raise OSError("disk full")
    monkeypatch.setattr(pr, "write", refuse)
    mark = len(rig.out.sent)
    n, ch = pad(2)
    at(1.0, save_down(), note(n, channel=ch))
    assert pr.bank[2] == "FIELD" and "TRIP 2" in lib.list("presets")
    assert "the show could not be written" in lib.warning
    # (review of PR #175) the slot does not hold the new preset: no blink,
    # and the log says it did not land, not "saved into slot 3"
    assert apc40.GREEN_BLINK not in leds(rig, n, ch, mark)
    assert not any(c == (n, ch) for c in [(k[2], k[1]) for k in rig.midi._hold_state()[1]])
    assert rig.midi.desk_log.events[-1].what == "save into slot 3: did not land there"
    at(1.1, note(n, 0, channel=ch), save_up())
    assert pr.save_into(2) is False and pr.bank[2] == "FIELD"           # the model says so
    monkeypatch.undo()

    def fail(name):
        raise OSError("read-only")
    monkeypatch.setattr(lib.presets, "save_as", fail)
    mark = len(rig.out.sent)
    n, ch = pad(1)
    at(2.0, save_down(), note(n, channel=ch))
    assert pr.bank[1] == "FACES" and apc40.GREEN_BLINK not in leds(rig, n, ch, mark)
    assert "read-only" in pr.bank_error


def test_the_hold_on_an_empty_pad_still_saves_and_a_filled_one_only_loads(rig):
    """#158's hold stays beside the two-handed save: an empty pad held
    saves into its slot; a filled pad held loads and writes nothing (the
    desk never overwrites, and the hold never makes a new preset over a
    filled slot — that is the two-handed save's)."""
    at = clocked(rig)
    lib, pr = rig.presets.lib, rig.presets
    at(0.0, *tap(4))
    n, ch = pad(9)
    at(1.0, note(n, channel=ch))
    at(1.0 + midi.HOLD_S)                                             # still down: it fires
    at(1.0 + 2 * midi.HOLD_S, note(n, 0, channel=ch))
    assert pr.bank[9] == "TRIP 2"
    files = user_files(lib)
    n, ch = pad(1)
    at(3.0, note(n, channel=ch))
    at(3.0 + midi.HOLD_S)
    at(3.0 + 2 * midi.HOLD_S, note(n, 0, channel=ch))
    assert lib.current("presets") == "FACES" and pr.bank[1] == "FACES"
    assert user_files(lib) == files


def test_save_into_and_save_empty_on_the_project(rig):
    """`Project.save_into` grew the filled case; `save_empty` is #158's
    hold (empty only). Neither overwrites a file."""
    pr = rig.presets
    pr.load_slot(4)
    assert pr.save_empty(1) is False and pr.bank[1] == "FACES"
    assert pr.save_into(1) is True and pr.bank[1] == "TRIP 2"
    assert pr.save_empty(9) is True and pr.bank[9] == "TRIP 3"
    assert pr.save_into(99) is False and pr.save_empty(-1) is False
    assert rig.reg["preset.select"].held == pr.save_empty
    assert rig.reg["preset.select"].save_into == pr.save_into


# --------------------------------------------------- the render toggles, both layers

def test_the_render_toggles_are_invariant_and_their_leds_show_the_live_state(rig):
    """Points, lines, faces and rotate (scene launch 1–4) mean the same on
    both layers — D6's list grows by four — and each LED shows the param's
    live state: after a press on either layer, after the panel moves it,
    and right after a load on either layer. Reset view (scene launch 5)
    stays the preset's."""
    t, reg = rig.midi.table, rig.reg
    for pid, n in TOGGLES:
        (b,) = t.route("note", 0, n)
        assert (b.target, b.op, b.layer, b.feedback) == (pid, "toggle", None, "led")
        assert b in t.active()
    (reset,) = t.route("note", 0, apc40.N_SCENE[4])
    assert (reset.target, reset.layer) == ("camera.reset", "preset")
    for layer in ("preset", "global"):
        if layer == "global":
            shift(rig)
        assert t.layer == layer
        for pid, n in TOGGLES:
            was = bool(reg[pid].value)
            push(rig, note(n), note(n, 0))
            assert bool(reg[pid].value) is not was, (layer, pid)
            assert leds(rig, n)[-1] == (0 if was else 1), (layer, pid)
            reg[pid].set(was)                                         # the panel moves it back
            rig.midi.poll()
            assert leds(rig, n)[-1] == (1 if was else 0), (layer, pid)
    # right after a load, on either layer: the loaded preset's values
    for under_shift in (False, True):
        if under_shift and t.layer == "preset":
            shift(rig)
        mark = len(rig.out.sent)
        push(rig, *tap(0))                                            # TUMBLE: points off, rest on
        assert t.layer == "preset"
        for pid, n in TOGGLES:
            assert leds(rig, n, 0, mark)[-1] == (1 if reg[pid].value else 0), pid
        assert [bool(reg[p].value) for p, _ in TOGGLES] == [False, True, True, True]


def test_an_older_presets_toggle_rows_drop_quietly_and_an_owners_row_with_a_note(rig):
    """A preset saved before C1 holds the four factory toggle rows on its
    desk (every factory file still does: decision 23, no library file is
    rewritten). A load drops them without a note — the session's rows do
    the same job (`routing.RETIRED_DESK_ROWS`) — and drops an owner's row
    on the SAVE button with the usual note. Loaded through a scratch
    library from tests/fixtures/desk-trust/."""
    lib, t = rig.presets.lib, rig.midi.table
    (lib.home / "presets").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "old-desk.json", lib.home / "presets" / "old-desk.json")
    lib.presets.load("OLD DESK")
    assert lib.current("presets") == "OLD DESK"
    assert lib.presets.desk_notes == [
        ("dropped note:7:52 → camera.reset: that control is invariant, the session's "
         "(plan 13 D6)")]
    assert [b.source for b in t.desk()] == ["cc:0:48", "cc:0:55", "note:0:86"]
    for (pid, n), want in zip(TOGGLES, (True, False, True, False)):
        assert bool(rig.reg[pid].value) is want
        (b,) = [x for x in t.active() if x.number == n and x.kind == "note"]
        assert b.layer is None
    rig.midi.poll()
    assert [leds(rig, n)[-1] for _p, n in TOGGLES] == [1, 0, 1, 0]
    assert not lib.is_dirty("presets")


def test_every_factory_file_still_holds_the_toggle_rows_and_loads_quietly(rig):
    """Decision 23: every file under hyperspace/library/ is byte-identical,
    so the factory presets still carry the four toggle rows (the generator
    writes them: `preset.file_desk`); each loads with no desk note."""
    from hyperspace import preset

    lib = rig.presets.lib
    rows = {(d["source"], d["target"]) for d in preset.desk_json(preset.file_desk())}
    assert {(f"note:0:{n}", pid) for pid, n in TOGGLES} <= rows
    assert not {(f"note:0:{n}", pid) for pid, n in TOGGLES} & {
        (b.source, b.target) for b in preset.fresh_desk()}
    for name in lib.list("presets"):
        lib.presets.load(name)
        assert lib.presets.desk_notes == [], name


def test_a_session_file_gains_the_toggles_and_the_save_once(tmp_path):
    """A `bindings.json` from before C1 has no row on scene launch 1–4 (they
    were the preset's) nor on track 8's clip stop: its next load adds the
    five factory rows, says so and writes the file back once; the next
    load is quiet. A row the owner put on one of those controls is kept,
    and that control gets no factory row."""
    added = [(f"note:0:{n}", pid, "toggle") for pid, n in TOGGLES] + [
        (f"note:{SAVE_CH}:{STOP}", SAVE_PARAM, "momentary")]
    new = {(s, t) for s, t, *_ in routing.APC_NEW_ROWS}
    assert {(s, t) for s, t, _op in added} <= new
    old = [b for b in Bindings.factory().bindings
           if routing.is_session_row(b) and (b.source, b.target) not in
           {(s, t) for s, t, _op in added}]
    path = bindings_path(tmp_path / "a")
    (tmp_path / "a").mkdir()
    Bindings(old, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    for s, pid, op in added:
        (b,) = t.route("note", int(s.split(":")[1]), int(s.split(":")[2]))
        assert (b.target, b.op, b.layer, b.feedback) == (pid, op, None, "led")
        assert f"added {s} → {pid} (the APC40 map of plan 24)" in t.notes
    again = Bindings.load(path, legacy_midi=None)
    assert again.notes == []
    # an owner's row on scene launch 1 is kept; that control gets nothing
    mine = Binding(f"note:0:{apc40.N_SCENE[0]}", "view.speed", "step", feedback="led")
    path = bindings_path(tmp_path / "b")
    (tmp_path / "b").mkdir()
    Bindings([*old, mine], path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    assert [b.target for b in t.route("note", 0, apc40.N_SCENE[0])] == ["view.speed"]


# --------------------------------------------------- every load relights the desk

def test_every_load_relights_the_whole_desk(rig):
    """A load re-sends every ring and LED the new preset and the session
    draw, and sends dark every other control on the desk — the whole
    layout, even one no row ever named (a light some other program left
    on) — on whichever layer the load came from."""
    t = rig.midi.table
    for under_shift in (False, True):
        if under_shift:
            shift(rig)
        mark = len(rig.out.sent)
        push(rig, *tap(2))
        assert t.layer == "preset"
        sent = rig.out.sent[mark:]
        notes = {(m.channel, m.note) for m in sent if m.type == "note_on"}
        for c in apc40.LAYOUT:
            kind, ch, num = c.source.split(":")
            if kind == "note":
                assert (int(ch), int(num)) in notes, c.glyph            # lit or dark: sent
        drawn = {b.control for b in t.active() if b.feedback}
        for c in apc40.LAYOUT:
            kind, ch, num = c.source.split(":")
            if kind == "note" and ("note", int(ch), int(num)) not in drawn:
                last = [m.velocity for m in sent if m.type == "note_on"
                        and (m.channel, m.note) == (int(ch), int(num))][-1]
                assert last == 0, c.glyph                               # undrawn: dark
        rings = {m.control - 8 for m in sent if m.type == "control_change"
                 and m.control - 8 in (*apc40.DEVICE_KNOBS, *apc40.TRACK_KNOBS)}
        assert rings == {*apc40.DEVICE_KNOBS, *apc40.TRACK_KNOBS}       # every ring set up


def test_a_load_lets_go_of_every_fader_the_preset_binds(rig):
    """Register row 44, changed by C1: a load re-arms soft pickup on every
    fader the new preset's desk binds, whether or not the load moved its
    param — each such fader picks up from the new preset, the same way
    every time. The session's faders (invariant, never moved by a preset,
    D9: the crossfader's dim, MASTER) keep their hold as before."""
    t, reg = rig.midi.table, rig.reg
    # a preset desk with a fader row (C2 moves S1–S8 there; a test row here)
    speed = Binding(f"cc:0:{apc40.CC_FADER}", "view.speed", "abs", layer="preset")
    for b in [x for x in t.bindings if x.source == speed.source]:
        t.bindings.remove(b)                                          # free S1 for the test
    t.set_desk([*t.desk(), speed])
    rig.midi.poll()
    reg["view.speed"].set_norm(0.5)
    reg["output.dim"].set_norm(0.5)
    rig.midi.poll()
    push(rig, cc(apc40.CC_FADER, 64), cc(apc40.CC_XFADE, 64))
    s1 = next(b for b in t.desk() if b.source == speed.source)
    xf = next(b for b in t.bindings if b.target == "output.dim")
    assert s1.caught and xf.caught
    t.set_desk(t.desk())                       # a load that moves neither param
    rig.midi.poll()
    s1 = next(b for b in t.desk() if b.source == speed.source)
    assert not s1.caught and xf.caught
    push(rig, cc(apc40.CC_FADER, 65))         # where the fader already is: caught at once
    assert s1.caught


# ------------------------------------------------------------ the desk event log

def test_the_desk_log_keeps_the_last_twenty_presses(rig):
    """The SYSTEM page's desk log: each press — the control, what it did,
    the layer it was read on ("both" for an invariant control) — newest
    first, twenty kept. A press that did nothing says so; a hold that fired
    and a two-handed save are events too."""
    at = clocked(rig)
    log = rig.midi.desk_log
    assert log.size == midi.DESK_LOG_SIZE == 20 and log.lines() == []
    at(0.0, *tap(4))
    e = log.events[-1]
    assert (e.control, e.layer) == ("G1·5 (clip 1·5)", "both")
    assert e.what == "Preset → TRIP"
    at(0.5, note(apc40.N_SCENE[0]))                                   # points, invariant
    assert log.events[-1].what == "Points → on" and log.events[-1].layer == "both"
    at(0.6, note(apc40.N_ACTIVATOR, channel=6))                       # nothing maps it
    assert log.events[-1].what == "nothing (no row on the preset layer)"
    assert log.events[-1].layer == "preset"
    shift(rig)
    assert (log.events[-1].what, log.events[-1].layer) == ("Shift → on", "both")
    at(1.0, note(apc40.N_CLIP[1], channel=2))                         # a band scene, global
    assert log.events[-1].layer == "global"
    assert log.events[-1].what == f"{rig.reg['scene.select'].label} → " \
                                  f"{rig.reg['scene.select'].text()}"
    at(2.0, save_down())
    at(2.1, *tap(14))
    assert log.events[-1].what == "saved into slot 15: TRIP 2"
    assert (log.events[-1].control, log.events[-1].layer) == ("G4·7 (clip 4·7)", "both")
    assert log.events[-2].what == "Save → on"
    assert log.events[-2].control == "G6·8 (clip stop 8)"
    at(2.2, save_up())
    n, ch = pad(1)
    at(3.0, note(n, channel=ch))
    at(3.0 + midi.HOLD_S)
    at(3.5 + midi.HOLD_S, note(n, 0, channel=ch))
    assert log.events[-1].what == "held: nothing saved (a filled pad only loads)"
    assert log.events[-2].what == "Preset → FACES"
    for i in range(30):
        at(4.0 + i, note(apc40.N_TAP), note(apc40.N_TAP, 0))
    assert len(log) == 20 and len(log.lines()) == 20
    tap_label = rig.reg["tempo.tap"].label
    assert set(log.lines()) == {f"{e.when}  B20 (TAP TEMPO)  {tap_label}  [both]"
                                for e in log.events}


def test_the_desk_log_lines_have_a_time_a_control_what_and_a_layer():
    log = midi.DeskLog(size=3, wall=lambda: "21:04:13")
    log.add("G1·3 (clip 1·3)", "Preset → FIELD", "both")
    log.add("D1 (device knob 1)", "nothing (no row on the global layer)", "global")
    assert log.lines() == [
        "21:04:13  D1 (device knob 1)  nothing (no row on the global layer)  [global]",
        "21:04:13  G1·3 (clip 1·3)  Preset → FIELD  [both]"]
    for k in range(5):
        log.add(f"c{k}", "x", "preset")
    assert [e.control for e in log.events] == ["c2", "c3", "c4"]


@pytest.mark.parametrize("missing", [True, False])
def test_the_system_page_helper_reads_the_log(rig, missing):
    """ui.desk_log_lines: the SYSTEM page's lines, with no imgui — none for
    an adapter from before a hot reload (no log) or with nothing pressed."""
    from hyperspace import ui

    if missing:
        rig.midi.__dict__.pop("desk_log", None)
        assert ui.desk_log_lines(None) == []
    push(rig, *tap(0))
    lines = ui.desk_log_lines(rig.midi)
    assert len(lines) == 1 and "Preset → TUMBLE" in lines[0]
