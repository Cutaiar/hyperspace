"""Idle lights (idle_lights.py): a desk's LEDs animate while it is untouched and
no app it gives way to (Rekordbox) runs; any input ends it, and it leaves every
light it drew dark. No hardware: fake ports and a clock the test moves."""

from types import SimpleNamespace as NS

import mido
import pytest
from test_midi import FakeIn, FakeOut, cc, note, rig  # noqa: F401 — the rig fixture

from hyperspace import idle_lights
from hyperspace.idle_lights import AppWatch, IdleLights, Light, from_entry, parse_never
from hyperspace.midi import MidiIO

# ---------------------------------------------------------------- the animator


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _anim(after=10.0, watch=None, pattern=lambda light, t: 1.0):
    clock = Clock()
    lights = (Light("note", 7, 0), Light("note", 7, 1), Light("cc", 0, 2, levels=None))
    return IdleLights(lights, after=after, pattern=pattern, watch=watch, clock=clock), clock


def test_it_starts_only_after_the_device_is_untouched_for_a_while():
    a, clock = _anim(after=10.0)
    assert a.tick() == [] and not a.running
    clock.t = 9.9
    assert a.tick() == []
    clock.t = 10.0
    assert a.tick() == [("note", 7, 0, 127), ("note", 7, 1, 127), ("cc", 0, 2, 127)]
    assert a.running


def test_a_frame_sends_only_the_lights_that_changed_and_no_faster_than_fps():
    a, clock = _anim(after=0.0)
    a.tick()
    clock.t = 0.001
    assert a.tick() == []                       # inside the frame interval
    clock.t = 1.0
    assert a.tick() == []                       # a new frame, nothing changed


def test_a_touch_ends_it_and_every_light_it_drew_goes_dark():
    lit = {"on": True}
    a, clock = _anim(after=5.0, pattern=lambda light, t: 1.0 if lit["on"] else 0.0)
    clock.t = 5.0
    a.tick()
    lit["on"] = False
    clock.t = 6.0
    a.tick()                                    # every light now 0: nothing to darken
    lit["on"] = True
    clock.t = 7.0
    a.tick()                                    # lit again
    a.touched()
    out = a.tick()
    assert sorted(out) == [("cc", 0, 2, 0), ("note", 7, 0, 0), ("note", 7, 1, 0)]
    assert a.ended and not a.running
    assert a.tick() == [] and not a.ended       # the next frame: quiet, waiting again
    clock.t = 12.0
    assert a.tick() and a.running               # untouched long enough: it starts again


def test_it_never_runs_while_an_app_it_yields_to_runs_and_ends_when_one_starts():
    procs = ["finder"]
    watch = AppWatch(["rekordbox"], look=lambda: procs, start=False)
    a, clock = _anim(after=0.0, watch=watch)
    watch.check()
    assert a.tick() and a.running
    procs.append("rekordbox")
    watch.check()
    assert a.tick() == [("note", 7, 0, 0), ("note", 7, 1, 0), ("cc", 0, 2, 0)]
    clock.t = 100.0
    assert a.tick() == [] and not a.running     # untouched for ages, still yielding
    procs.remove("rekordbox")
    watch.check()
    assert a.tick() and a.running


def test_the_app_watch_matches_part_of_a_name_ignoring_case():
    w = AppWatch(["Rekordbox"], look=lambda: ["launchd", "rekordboxagent"], start=False)
    assert w.check()
    w = AppWatch(["rekordbox"], look=lambda: ["serato dj pro"], start=False)
    assert not w.check()
    assert AppWatch([], look=lambda: ["rekordbox"], start=False).check() is False


def test_the_app_watch_thread_looks_on_its_own_and_stops():
    seen = []
    w = AppWatch(["rekordbox"], look=lambda: seen.append(1) or ["rekordbox"])
    for _ in range(200):
        if w.running:
            break
        import time
        time.sleep(0.005)
    w.stop()
    assert w.running and seen


def test_end_now_darkens_without_asking_the_desk_to_redraw():
    a, _clock = _anim(after=0.0)
    a.tick()
    assert len(a.end_now()) == 3 and not a.ended and not a.running
    assert a.end_now() == []


def test_a_light_maps_brightness_to_its_levels():
    grid = Light("note", 0, 0x35, levels=(0, 1, 5, 3))
    assert [grid.value(b) for b in (0.0, 0.3, 0.6, 1.0)] == [0, 1, 5, 3]
    meter = Light("cc", 0, 2, levels=None)
    assert [meter.value(b) for b in (0.0, 0.5, 1.0, 2.0, float("nan"))] == [0, 64, 127, 127, 0]


@pytest.mark.parametrize("name", sorted(idle_lights.SETS))
@pytest.mark.parametrize("pattern", sorted(idle_lights.PATTERNS))
def test_every_set_and_pattern_stays_in_midi_range(name, pattern):
    lights = idle_lights.SETS[name]()
    assert len({lt.key for lt in lights}) == len(lights)       # no light twice
    for t in (0.0, 0.37, 1.2, 3.9):
        for lt in lights:
            v = lt.value(idle_lights.PATTERNS[pattern](lt, t))
            assert 0 <= v <= 127 and 0 <= lt.channel <= 15 and 0 <= lt.number <= 127


# ---------------------------------------------------------------- the entry


def test_from_entry_reads_the_shorthands_and_the_table():
    assert from_entry(None) is None and from_entry(False) is None
    a = from_entry("ddj-flx4", start_watch=False)
    assert a is not None and a.after == idle_lights.AFTER_S
    assert a.watch is not None and a.watch.names == ("rekordbox",)    # yields by default
    b = from_entry(True, default_set="apc40", start_watch=False)
    assert b is not None and len(b.lights) == 45
    c = from_entry({"lights": "ddj-flx4", "after": 5, "pattern": "breathe", "yield_to": [],
                    "never": ["note:0:11", "note@ddj-flx4:1:11", "cc:0:2"]}, start_watch=False)
    assert c is not None and c.after == 5.0 and c.watch is None
    keys = {lt.key for lt in c.lights}
    assert ("note", 0, 11) not in keys and ("note", 1, 11) not in keys
    assert ("cc", 0, 2) not in keys and ("cc", 1, 2) in keys


@pytest.mark.parametrize("bad", [
    "nope", True, 7, {"lights": "ddj-flx4", "pattern": "spin"},
    {"lights": "ddj-flx4", "after": -1}, {"lights": "ddj-flx4", "after": float("nan")},
    {"lights": "ddj-flx4", "never": ["sysex:0:1"]}, {"lights": "ddj-flx4", "never": ["note:a:1"]},
])
def test_a_bad_entry_says_what_is_wrong(bad):
    with pytest.raises(ValueError, match="idle"):
        from_entry(bad, start_watch=False)


def test_parse_never():
    assert parse_never(["note:7:0", "cc@x:1:2"]) == {("note", 7, 0), ("cc", 1, 2)}


# ---------------------------------------------------------------- on a desk


def _desk(rig, profile, after=1.0):  # noqa: F811
    """A desk with an idle animation and a clock the test moves; nothing yields."""
    clock = Clock()
    inp, out = FakeIn(), FakeOut()
    if profile == "generic":
        rig.midi.table.midi_roles = ("apc40", "flx4")
        io = MidiIO(rig.reg, rig.midi.table, port="DDJ-FLX4", profile="generic", inp=inp,
                    out=out, learner=rig.midi.learner, role="flx4")
        name = "ddj-flx4"
    else:
        io, inp, out, name = rig.midi, rig.inp, rig.out, "apc40"
    io.idle = from_entry({"lights": name, "after": after, "yield_to": []}, clock=clock)
    return NS(io=io, inp=inp, out=out, clock=clock)


def _lights(msgs):
    return {(m.type, m.channel, getattr(m, "note", getattr(m, "control", None))):
            getattr(m, "velocity", getattr(m, "value", None)) for m in msgs}


def test_a_generic_desk_sends_nothing_until_idle_then_animates_then_darkens_on_a_touch(rig):  # noqa: F811
    d = _desk(rig, "generic")
    d.io.poll()
    assert d.out.sent == []                     # generic: nothing is ever sent but this
    d.clock.t = 1.0
    d.io.poll()
    first = list(d.out.sent)
    assert first and d.io.idle.running
    assert all(m.type in ("note_on", "control_change") for m in first)
    d.out.sent.clear()
    d.inp.queue.append(note(0, 127, channel=7))     # a pad press
    d.io.poll()
    assert not d.io.idle.running
    dark = _lights(d.out.sent)
    lit = {k for k, v in _lights(first).items() if v}
    assert lit and lit <= set(dark) and set(dark.values()) == {0}


def test_a_clock_tick_does_not_count_as_a_touch(rig):  # noqa: F811
    d = _desk(rig, "generic")
    d.clock.t = 1.0
    d.io.poll()
    d.inp.queue.append(mido.Message("clock"))
    d.clock.t = 2.0
    d.io.poll()
    assert d.io.idle.running


def test_a_sysex_answer_to_another_app_counts_as_a_touch(rig):  # noqa: F811
    d = _desk(rig, "generic")
    d.clock.t = 1.0
    d.io.poll()
    d.inp.queue.append(mido.Message("sysex", data=[0x00, 0x40, 0x05]))
    d.io.poll()
    assert not d.io.idle.running


def test_the_apc40_holds_its_feedback_while_idle_and_redraws_it_after(rig, monkeypatch):  # noqa: F811
    d = _desk(rig, "apc40")
    d.io.poll()
    calls = {"feedback": 0, "redraw": 0}
    real_fb, real_rd = d.io.feedback, d.io.redraw

    def fb():
        calls["feedback"] += 1
        real_fb()

    def rd(**kw):
        calls["redraw"] += 1
        real_rd(**kw)

    monkeypatch.setattr(d.io, "feedback", fb)
    monkeypatch.setattr(d.io, "redraw", rd)
    d.clock.t = 1.0
    d.io.poll()
    assert d.io.idle.running and calls == {"feedback": 0, "redraw": 0}
    d.out.sent.clear()
    d.inp.queue.extend([cc(0x30, 64), cc(0x30, 70)])    # a track knob turned
    d.io.poll()
    assert not d.io.idle.running and calls["redraw"] == 1 and calls["feedback"] >= 1


def test_closing_a_desk_mid_animation_leaves_nothing_lit(rig):  # noqa: F811
    d = _desk(rig, "generic")
    d.clock.t = 1.0
    d.io.poll()
    d.out.sent.clear()
    d.io.close()
    assert d.out.sent and {m.velocity if m.type == "note_on" else m.value
                           for m in d.out.sent} == {0}


def test_a_desk_made_before_idle_lights_reads_none(rig):  # noqa: F811
    d = rig.midi
    d.__dict__.pop("idle", None)
    assert d.idle is None
    d.poll()


# ---------------------------------------------------------------- what counts as a touch

# what the FLX4 sent in the probe's 120 s with no hand on it: its crossfader's
# 14-bit pair on channel 6, the MSB (CC 31) wandering a step, the LSB (CC 63) anywhere
FLX4_TWITCH = ["B6 1F 43", "B6 3F 1E", "B6 1F 42", "B6 3F 6B", "B6 1F 42", "B6 3F 37",
               "B6 1F 42", "B6 3F 03", "B6 1F 41", "B6 3F 4F", "B6 1F 41", "B6 3F 1B"]


def _twitch_msgs():
    return [mido.Message.from_hex(h) for h in FLX4_TWITCH]


def test_the_probes_crossfader_twitch_is_not_a_touch():
    a, clock = _anim(after=1.0)
    clock.t = 1.0
    a.tick()
    for k, m in enumerate(_twitch_msgs()):
        clock.t = 1.0 + (k // 2) * 0.44          # a pair, back to back, ~2 a second
        assert not a.is_touch("cc", m.channel, m.control, m.value), m.hex()
    assert a.running


def test_a_real_move_is_a_touch():
    a, clock = _anim()
    assert not a.is_touch("cc", 6, 31, 66)               # the first: only where it is
    clock.t = 1.0
    assert not a.is_touch("cc", 6, 31, 67)               # a twitch
    clock.t = 2.0
    assert a.is_touch("cc", 6, 31, 70)                   # three steps: moved
    assert a.is_touch("note", 7, 0, 127)                 # a pad
    assert a.is_touch("note", 7, 0, 0)
    assert a.is_touch("sysex", 0, 0, 0)


def test_a_jog_spin_is_a_touch_by_its_rate():
    a, clock = _anim()
    said = []
    for k in range(idle_lights.BURST_N):
        clock.t = 5.0 + k * 0.02
        said.append(a.is_touch("cc", 0, 0x22, 65))       # one value, over and over
    assert said[-1] and not any(said[:-1])


def test_a_lone_cc_32_to_63_with_no_msb_heard_is_its_own_control():
    a, clock = _anim()
    a.is_touch("cc", 0, 40, 10)
    clock.t = 1.0
    assert a.is_touch("cc", 0, 40, 90)


def test_a_twitching_crossfader_on_a_desk_lets_the_animation_run(rig):  # noqa: F811
    d = _desk(rig, "generic")
    d.clock.t = 1.0
    d.io.poll()
    msgs = _twitch_msgs()
    for k in range(0, len(msgs), 2):
        d.clock.t = 1.0 + k * 0.22
        d.inp.queue.extend(msgs[k:k + 2])               # each pair in one poll
        d.io.poll()
    assert d.io.idle.running
    d.inp.queue.append(note(0, 127, channel=7))
    d.io.poll()
    assert not d.io.idle.running


def test_reloop_is_not_on_the_flx4():
    assert not any(lt.number == 0x4D for lt in idle_lights.flx4())
    assert len(idle_lights.flx4()) == 30


# ---------------------------------------------------------------- a touch ends the animation


def test_a_touch_ends_it_even_with_no_idle_delay():
    a, clock = _anim(after=0.0)
    a.tick()
    assert a.running
    a.touched()
    assert a.tick() and a.ended and not a.running      # darkened this frame
    clock.t = 1.0
    assert a.tick() and a.running                       # and back the next


def test_an_apc40_track_knob_ends_it_after_its_device_knob_was_turned():
    a, clock = _anim()
    for k, v in enumerate((10, 30, 50)):                # device knob 1 (CC 16)
        clock.t = k * 1.0
        a.is_touch("cc", 0, 16, v)
    said = []
    for k, v in enumerate((20, 40, 60, 80)):            # track knob 1 (CC 48), later
        clock.t = 10.0 + k * 0.3
        said.append(a.is_touch("cc", 0, 48, v))
    assert said[1:] == [True, True, True]


def test_an_lsb_is_one_only_straight_after_its_msb():
    a, clock = _anim()
    a.is_touch("cc", 6, 31, 66)
    assert not a.is_touch("cc", 6, 63, 10)              # straight after: the LSB
    clock.t = 1.0
    a.is_touch("cc", 6, 31, 66)
    clock.t = 1.0 + 2 * idle_lights.PAIR_S
    a.is_touch("cc", 6, 63, 10)                         # too late: a control of its own
    clock.t = 2.0
    assert a.is_touch("cc", 6, 63, 90)


def test_the_pattern_is_looked_up_by_name_each_frame(monkeypatch):
    a = from_entry({"lights": "ddj-flx4", "after": 0, "yield_to": []}, clock=Clock())
    assert a is not None and a.pattern_name == "wave"
    monkeypatch.setitem(idle_lights.PATTERNS, "wave", lambda light, t: 1.0)   # a reload's edit
    assert {v for *_k, v in a.tick()} == {127}


def test_the_desk_hands_its_animator_and_watch_to_the_hot_reloader():
    from hyperspace import devices
    idle = from_entry({"lights": "ddj-flx4"}, start_watch=False)
    io = NS(idle=idle)
    pairs = {(m, c) for _, m, c in devices.MidiDevice("flx4", io=io).targets()}
    assert pairs == {("midi", "MidiIO"), ("idle_lights", "IdleLights"),
                     ("idle_lights", "AppWatch")}
    assert {(m, c) for _, m, c in devices.MidiDevice("apc40", io=NS(idle=None)).targets()} \
        == {("midi", "MidiIO")}
