"""Plan 45 V2 — the media mixer (hyperspace/media/mixer.py) and the two
params per channel that drive it (`media.<c>.audio`, `media.<c>.gain`).

No audio device: the mixer is handed a fake stream factory whose stream
keeps its callback for the test to pull blocks through, and the channels
hold fake video sources whose `audio` is a fake soundtrack recording each
`read(at, n)` and each `enable` / `disable`. The rule under test is plan
45's: the transport is the one clock — the callback reads at the position
the last poll stepped it to, and moves nothing itself."""

import threading
import time

import numpy as np
import pytest
from test_media_channels import FakeOpener, FakeSource, Here

from hyperspace.media import mixer as M
from hyperspace.media.channels import HOLD_SPEED, OFF_FRAMES, MediaState
from hyperspace.media.video import AUDIO_RATE

DT = 1 / 60


class FakeTrack:
    """A soundtrack: every sample `value` on both sides; records reads."""

    def __init__(self, value=0.25, *, raises=False):
        self.value, self.raises = value, raises
        self.enabled = False
        self.enables = self.disables = 0
        self.reads: list[tuple[int, int]] = []
        self.outs: list = []

    def enable(self):
        self.enabled = True
        self.enables += 1

    def disable(self):
        self.enabled = False
        self.disables += 1

    def read(self, at, n, out=None):
        self.reads.append((at, n))
        self.outs.append(out)
        if self.raises:
            raise RuntimeError("bad read")
        if out is None:
            return np.full((n, 2), self.value, np.float32)
        out = out[:n]
        out.fill(self.value)
        return out


class Video(FakeSource):
    def __init__(self, sid, opener, **kw):
        super().__init__(sid, opener, timed=True, duration=10.0, kind="video")
        self.audio = FakeTrack(**kw)


class VideoOpener(FakeOpener):
    """Opens `Video`s; `values[sid]` sets that video's sample value."""

    def __init__(self, values=None, raises=()):
        super().__init__()
        self.values, self.raises = values or {}, set(raises)

    def __call__(self, sid, resolver):
        if sid.endswith(".png"):
            return super().__call__(sid, resolver)      # a still: no `audio`
        if sid.startswith("ndi:"):                      # a live feed: no `audio`
            return FakeSource(sid, self, kind="ndi")
        s = Video(sid, self, value=self.values.get(sid, 0.25), raises=sid in self.raises)
        self.made.append(s)
        return s


class FakeStream:
    def __init__(self, **kw):
        self.kw = kw
        self.callback = kw["callback"]
        self.started = self.aborted = self.closed = False
        self.active = True
        self.abort_s = 0.0          # how long abort takes (a device that will not stop)

    def start(self):
        self.started = True

    def abort(self):
        if self.abort_s:
            time.sleep(self.abort_s)
        self.aborted = True

    def close(self):
        self.closed = True

    def pull(self, frames=M.BLOCK, status=None):
        out = np.ones((frames, 2), np.float32) * 9     # garbage the callback must overwrite
        self.callback(out, frames, None, status)
        return out


class Factory:
    def __init__(self, gate: threading.Event | None = None, fail=False):
        self.made: list[FakeStream] = []
        self.gate, self.fail = gate, fail
        self.calls = 0

    def __call__(self, **kw):
        self.calls += 1
        if self.gate is not None:
            self.gate.wait()
        if self.fail:
            raise OSError("no output device")
        s = FakeStream(**kw)
        self.made.append(s)
        return s


def rig(*sids, values=None, raises=(), gate=None, fail=False):
    op = VideoOpener(values, raises)
    m = MediaState(Here(*sids), opener=op)
    f = Factory(gate, fail)
    m.mixer = M.Mixer(make=f)
    for k, sid in enumerate(sids):
        m.assign("abcdefgh"[k], 0, sid)
    return m, op, f


def settle(m, timeout=2.0) -> None:
    """Wait for an open under way (the opener clears itself when done)."""
    t = m.mixer._opener
    if t is not None:
        t.join(timeout)


def opened(m, f, timeout=2.0) -> FakeStream:
    settle(m, timeout)
    assert len(f.made) == 1 and m.mixer.state == "open"
    return f.made[0]


def track(m, c):
    return m.channels[c].source.audio


# ---------------------------------------------------------------- the sum

def test_the_callback_sums_each_heard_channel_read_at_its_playhead_times_its_gain():
    m, _, f = rig("shared:a.mp4", "shared:b.mp4", "shared:c.mp4",
                  values={"shared:a.mp4": 0.2, "shared:b.mp4": 0.3, "shared:c.mp4": 0.9})
    a, b, c = (m.channels[k] for k in "abc")
    a.play_audio, a.gain = True, 0.5
    b.play_audio = True
    c.gain = 1.0                              # c's sound is off: never read
    m.poll(DT, 0.0)
    s = opened(m, f)
    assert s.kw["samplerate"] == AUDIO_RATE and s.kw["channels"] == 2 and s.started
    out = s.pull()
    assert out.dtype == np.float32 and out.shape == (M.BLOCK, 2)
    assert np.allclose(out, 0.2 * 0.5 + 0.3)
    for ch in (a, b):
        at = round(ch.transport.playhead * AUDIO_RATE)
        assert ch.source.audio.reads == [(at, M.BLOCK)]
    assert track(m, "c").reads == [] and not track(m, "c").enabled


def test_the_sum_is_clipped_at_one():
    m, _, f = rig("shared:a.mp4", "shared:b.mp4",
                  values={"shared:a.mp4": 0.8, "shared:b.mp4": 0.7})
    for c in "ab":
        m.channels[c].play_audio = True
    m.poll(DT, 0.0)
    assert np.allclose(opened(m, f).pull(), M.CEILING)


def test_no_voice_is_silence():
    m, _, f = rig("shared:a.mp4")
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)
    m.channels["a"].play_audio = False
    m.poll(DT, 0.1)
    assert not s.pull().any()


# ---------------------------------------------------------------- the one clock

def test_the_callback_reads_the_transports_stepped_position_and_moves_nothing():
    m, _, f = rig("shared:a.mp4")
    ch = m.channels["a"]
    ch.play_audio = True
    m.poll(DT, 0.0)
    s, tr = opened(m, f), ch.transport
    s.pull()
    s.pull()                                    # no step between: the same `at`
    reads = track(m, "a").reads
    assert reads[0] == reads[1] == (round(tr.playhead * AUDIO_RATE), M.BLOCK)
    before = tr.playhead
    s.pull()
    assert tr.playhead == before, "the callback never moves the transport"
    m.poll(DT, 0.1)                             # one step: the next callback is there
    assert tr.playhead == pytest.approx(before + DT)
    s.pull()
    assert reads[-1] == (round(tr.playhead * AUDIO_RATE), M.BLOCK)
    assert reads[-1][0] - reads[0][0] == round(DT * AUDIO_RATE)
    ch.pos = 0.5                                # a scrub: the sound lands with the picture
    m.poll(DT, 0.2)
    s.pull()
    assert reads[-1][0] == round(5.0 * AUDIO_RATE)
    assert not any(hasattr(m.mixer, k) for k in ("_played", "position", "_offset"))


def test_a_hold_is_silence_not_one_block_repeated():
    m, _, f = rig("shared:a.mp4")
    ch = m.channels["a"]
    ch.play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)
    ch.rate = 0.0
    m.poll(DT, 0.1)
    assert m.mixer.playing == 0 and not s.pull().any()
    assert track(m, "a").enabled, "a hold keeps the samples: play resumes at once"


def test_gain_zero_reads_nothing():
    m, _, _ = rig("shared:a.mp4")
    ch = m.channels["a"]
    ch.play_audio, ch.gain = True, 0.0
    m.poll(DT, 0.0)
    assert m.mixer.playing == 0
    ch.gain = float("nan")
    m.poll(DT, 0.1)
    assert m.mixer.playing == 0


# ---------------------------------------------------------------- the toggle

def test_the_toggle_enables_and_disables_exactly_on_a_flip():
    m, _, _ = rig("shared:a.mp4")
    ch = m.channels["a"]
    m.poll(DT, 0.0)
    t = track(m, "a")
    assert (t.enables, t.disables) == (0, 0), "nothing until something asks"
    ch.play_audio = True
    for k in range(3):
        m.poll(DT, 0.1 + k * DT)
    assert (t.enables, t.disables) == (1, 0)
    ch.play_audio = False
    for k in range(OFF_FRAMES - 1):
        m.poll(DT, 0.2 + k * DT)
    assert m.drain(2.0) and (t.enables, t.disables) == (1, 0), "let go only after a while"
    m.poll(DT, 0.9)
    assert m.drain(2.0)                         # the disable runs on the closer
    assert (t.enables, t.disables) == (1, 1)
    ch.play_audio = True
    m.poll(DT, 0.3)
    assert (t.enables, t.disables) == (2, 1)


def test_a_slot_change_while_on_enables_the_new_and_disables_the_old():
    m, _, _ = rig("shared:a.mp4", "shared:b.mp4")
    m.assign("a", 1, "shared:b.mp4")
    ch = m.channels["a"]
    ch.play_audio = True
    m.poll(DT, 0.0)
    old = track(m, "a")
    ch.slot = 1.0
    m.poll(DT, 0.1)
    new = track(m, "a")
    assert new is not old
    assert m.drain(2.0)
    # the old track ends with its source's `close`: one closer job, no `_Silence`
    assert (old.enables, old.disables) == (1, 0) and m.closer.done == 1
    assert (new.enables, new.disables) == (1, 0)
    assert m.mixer.voices[0][0] is new


class SlowOff(FakeTrack):
    """A soundtrack whose `disable` is held mid-way (the join of a thread
    stuck in `av.open`); it counts an enable landing inside a disable."""

    def __init__(self):
        super().__init__()
        self.gate, self.inside = threading.Event(), threading.Event()
        self.overlaps = 0
        self._in = False

    def enable(self):
        if self._in:
            self.overlaps += 1
        super().enable()

    def disable(self):
        self._in = True
        self.enabled = False
        self.inside.set()
        self.gate.wait(5.0)
        self.disables += 1
        self._in = False


def slow(m) -> SlowOff:
    """Channel a's source opened, its soundtrack swapped for a `SlowOff`."""
    m.poll(DT, 0.0)
    t = m.channels["a"].source.audio = SlowOff()
    return t


def test_an_enable_never_lands_inside_a_disable():
    """Review 1: off long enough for the disable to start on the closer,
    then on again while it is still inside it: the frame thread does not
    enable then; the closer enables once its disable is done, so the track
    ends enabled, with no overlap, and the next frames add nothing."""
    m, _, _ = rig("shared:a.mp4")
    ch = m.channels["a"]
    t = slow(m)
    ch.play_audio = True
    m.poll(DT, 0.0)
    assert t.enables == 1
    ch.play_audio = False
    for k in range(OFF_FRAMES):
        m.poll(DT, k * DT)
    assert t.inside.wait(2.0)                   # the closer is inside the disable
    ch.play_audio = True
    for k in range(3):
        m.poll(DT, 1.0 + k * DT)
    assert t.enables == 1 and not t.enabled, "no enable while the disable runs"
    t.gate.set()
    assert m.drain(2.0)
    assert (t.enables, t.disables, t.overlaps) == (2, 1, 0) and t.enabled
    for k in range(3):
        m.poll(DT, 2.0 + k * DT)
    assert t.enables == 2


def test_on_and_off_again_while_a_disable_runs_is_one_disable_and_no_enable():
    m, _, _ = rig("shared:a.mp4")
    ch = m.channels["a"]
    t = slow(m)
    ch.play_audio = True
    m.poll(DT, 0.0)
    ch.play_audio = False
    for k in range(OFF_FRAMES):
        m.poll(DT, k * DT)
    assert t.inside.wait(2.0)
    for flip in range(6):                       # on, off, on … while it is held
        ch.play_audio = flip % 2 == 0
        m.poll(DT, 1.0 + flip * DT)
    ch.play_audio = False
    for k in range(OFF_FRAMES + 2):
        m.poll(DT, 2.0 + k * DT)
    t.gate.set()
    assert m.drain(2.0)
    assert (t.disables, t.enables, t.overlaps) == (1, 1, 0) and not t.enabled


def test_a_lane_flicking_the_toggle_queues_nothing():
    """Review 2: a toggle flipped every frame (a lane, an LFO) never stays
    off `OFF_FRAMES`, so nothing is disabled or re-decoded; the sound is in
    the mix only on the frames it is on."""
    m, _, _ = rig("shared:a.mp4")
    ch = m.channels["a"]
    for k in range(120):
        ch.play_audio = k % 2 == 0
        m.poll(DT, k * DT)
        assert m.mixer.playing == (1 if ch.play_audio else 0)
    assert m.drain(2.0)
    t = track(m, "a")
    assert (t.enables, t.disables) == (1, 0) and m.closer.done == 0


def test_a_jogs_dying_coast_is_silence():
    """Review 3: a jog let go at rate 0 leaves the spring's coast decaying
    toward 0 for many frames; under `HOLD_SPEED` it is a hold, so the
    callback is never asked to repeat one block."""
    m, _, f = rig("shared:a.mp4")
    ch = m.channels["a"]
    ch.play_audio, ch.rate, ch.jog = True, 0.0, 0.5
    for k in range(20):
        m.poll(DT, k * DT)
    assert m.mixer.playing == 1                 # the jog moves the clip: heard
    ch.jog = 0.0
    tr = ch.transport
    for k in range(600):
        m.poll(DT, 1.0 + k * DT)
        if abs(tr.speed) < HOLD_SPEED:
            assert m.mixer.playing == 0, tr.speed
    assert 0.0 < abs(tr.speed) < HOLD_SPEED or tr.speed == 0.0
    assert m.mixer.playing == 0 and not opened(m, f).pull().any()


def test_a_still_and_a_live_feed_add_nothing_and_open_no_stream():
    m, _, f = rig("shared:x.png", "ndi:cam")
    for c in "ab":
        m.channels[c].play_audio = True
    m.poll(DT, 0.0)
    assert m.channels["a"].source.kind == "still" and m.channels["b"].source.kind == "ndi"
    assert m.mixer.voices == () and m.mixer.state == "off" and f.calls == 0


def test_a_once_clip_parked_at_its_end_is_silence():
    """Second review 1: at loop `once` the playhead clamps at the duration
    with the speed still 1; a track that outlasts the picture would be
    re-read one block a frame there — a buzz. Parked at the end: silent."""
    m, _, f = rig("shared:a.mp4")
    ch = m.channels["a"]
    ch.play_audio, ch.loop = True, 2                # once
    ch.pos = 0.99
    m.poll(DT, 0.0)
    ch.pos = 0.995                                  # (a scrub near the end, then let go)
    m.poll(DT, 0.1)
    assert m.mixer.playing == 1                     # still short of the end: heard
    for k in range(60):                             # 0.05 s of clip left: it parks
        m.poll(DT, 0.2 + k * DT)
    tr = ch.transport
    assert tr.playhead == tr.duration and tr.speed == 1.0
    assert m.mixer.playing == 0 and not opened(m, f).pull().any()


def test_reverse_and_pingpongs_way_back_are_silence():
    """Second review 1: a forward block under a backward picture is wrong;
    reverse is V4's, so a channel moving backwards is left out — a
    negative rate, and pingpong's return leg at a positive one."""
    m, _, _ = rig("shared:a.mp4", "shared:b.mp4")
    a, b = m.channels["a"], m.channels["b"]
    a.play_audio, a.rate = True, -1.0
    b.play_audio, b.loop = True, 1                  # pingpong
    b.pos = 0.999
    m.poll(DT, 0.0)
    b.pos = 0.9995
    m.poll(DT, 0.1)
    for k in range(10):                             # past the end: on the way back
        m.poll(DT, 0.2 + k * DT)
    assert b.transport.direction == -1.0 and b.transport.speed == 1.0
    assert m.mixer.voices == ()
    assert m.mixer.state != "off", "both still ask: the stream is up for when they turn"


def test_an_enable_that_raises_is_tried_again_next_frame():
    """Second review 3: `heard` is set only once `on` returned, so an
    enable that raised is retried rather than forgotten."""
    m, _, _ = rig("shared:a.mp4")
    ch = m.channels["a"]
    m.poll(DT, 0.0)
    t = track(m, "a")
    real, calls = t.enable, []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise OSError("not yet")
        real()

    t.enable = flaky
    ch.play_audio = True
    m.poll(DT, 0.1)
    assert ch.heard is None and not t.enabled
    m.poll(DT, 0.2)
    assert ch.heard is t and t.enabled and len(calls) == 2


def test_the_callback_reads_into_its_own_buffers():
    """Second review 6: once warm the callback allocates nothing: every
    voice is read into the mixer's one voice buffer (`read(..., out=)`)
    and summed into its one mix buffer, the same arrays callback after
    callback."""
    m, _, f = rig("shared:a.mp4", "shared:b.mp4",
                  values={"shared:a.mp4": 0.25, "shared:b.mp4": 0.5})
    for c in "ab":
        m.channels[c].play_audio = True
    m.channels["b"].gain = 0.5
    m.poll(DT, 0.0)
    s = opened(m, f)
    mix, one = m.mixer._mix, m.mixer._one
    for _ in range(3):
        assert np.allclose(s.pull(), 0.25 + 0.25)
    assert m.mixer._mix is mix and m.mixer._one is one
    for c in "ab":
        assert all(o is one for o in track(m, c).outs)


def test_a_read_that_raises_is_contained():
    m, _, f = rig("shared:a.mp4", "shared:b.mp4", raises=("shared:a.mp4",),
                  values={"shared:b.mp4": 0.5})
    for c in "ab":
        m.channels[c].play_audio = True
    m.poll(DT, 0.0)
    out = opened(m, f).pull()
    assert np.allclose(out, 0.5) and m.mixer.errors == 1


def test_a_wrong_shape_and_a_broken_voice_list_are_silence_not_a_raise():
    mx = M.Mixer(make=Factory())

    class Short(FakeTrack):
        def read(self, at, n, out=None):
            return np.zeros((n - 1, 2), np.float32)

    mx.voices = ((Short(), 0.0, 1.0),)
    out = np.ones((8, 2), np.float32)
    mx._callback(out, 8, None, None)
    assert not out.any() and mx.errors == 1
    mx.voices = (("not a voice",),)
    out[:] = 1
    mx._callback(out, 8, None, None)            # anything else wrong: silence
    assert not out.any()


def test_an_underflow_is_counted():
    m, _, f = rig("shared:a.mp4")
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)
    s.pull(status=type("Flags", (), {"output_underflow": True})())
    s.pull(status=type("Flags", (), {"output_underflow": False})())
    assert m.mixer.underruns == 1
    assert "1 playing" in m.mixer.line() and "1 underruns" in m.mixer.line()


def test_a_read_error_is_counted_but_never_warns():
    """Review 5: the line says "read errors"; only a stream that failed warns."""
    from types import SimpleNamespace as NS

    from hyperspace import ui_media

    m, _, f = rig("shared:a.mp4", raises=("shared:a.mp4",))
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    opened(m, f).pull()
    text, warn = ui_media.mixer_line(NS(media=NS(state=m)))
    assert "1 read errors" in text and not warn and not m.mixer.failed
    m.mixer.state = "error: OSError: gone"
    assert ui_media.mixer_line(NS(media=NS(state=m)))[1] is True


# ---------------------------------------------------------------- the stream

def test_the_stream_opens_on_the_first_toggle_and_not_before():
    m, _, f = rig("shared:a.mp4")
    for k in range(5):
        m.poll(DT, k * DT)
    assert f.calls == 0 and m.mixer.state == "off" and m.mixer.line() == ""
    m.channels["a"].play_audio = True
    m.poll(DT, 1.0)
    s = opened(m, f)
    m.channels["a"].play_audio = False
    for k in range(5):                          # off again: left open, playing silence
        m.poll(DT, 2.0 + k)
    m.channels["a"].play_audio = True
    m.poll(DT, 9.0)
    assert f.calls == 1 and f.made == [s] and not s.closed


def test_the_open_never_holds_the_frame_thread():
    gate = threading.Event()
    m, _, f = rig("shared:a.mp4", gate=gate)
    m.channels["a"].play_audio = True
    t0 = time.monotonic()
    m.poll(DT, 0.0)
    m.poll(DT, 0.1)
    assert time.monotonic() - t0 < 0.2 and m.mixer.state == "opening"
    gate.set()
    opened(m, f)


def test_a_failed_open_is_said_and_tried_again_later():
    m, _, f = rig("shared:a.mp4", fail=True)
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    settle(m)
    assert m.mixer.state.startswith("error: OSError") and m.mixer.failed
    m.poll(DT, 1.0)
    assert f.calls == 1                         # not every frame
    f.fail = False
    m.mixer._failed_at -= M.RETRY_S             # RETRY_S since the failure
    m.poll(DT, 2.0)
    opened(m, f)


def test_the_retry_counts_from_when_the_open_failed():
    """Review 7: an open that took long to fail waits RETRY_S from its
    failure, not from its start."""
    gate = threading.Event()
    m, _, f = rig("shared:a.mp4", gate=gate, fail=True)
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    began = time.monotonic()
    time.sleep(0.05)
    gate.set()
    settle(m)
    assert m.mixer._failed_at >= began + 0.05
    m.poll(DT, 1.0)
    assert f.calls == 1


def test_sound_on_during_a_hold_opens_the_stream():
    """Review 6: the toggle asks, heard or not yet: at rate 0 or gain off
    the stream comes up, so the sound is there the moment play resumes."""
    m, _, f = rig("shared:a.mp4", "shared:b.mp4")
    m.channels["a"].rate = 0.0
    m.channels["b"].gain = 0.0
    for c in "ab":
        m.channels[c].play_audio = True
    m.poll(DT, 0.0)
    assert m.mixer.playing == 0
    opened(m, f)


def test_a_stream_that_stops_under_us_is_opened_again():
    """Review 4: a device unplugged ends the stream (`active` false); the
    next feed drops it, SYSTEM warns, and RETRY_S later a new one opens."""
    m, _, f = rig("shared:a.mp4")
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)
    s.active = False
    m.poll(DT, 0.1)
    assert m.mixer.failed and "stopped" in m.mixer.state and m.mixer._stream is None
    deadline = time.monotonic() + 2.0
    while not s.closed and time.monotonic() < deadline:
        time.sleep(0.01)
    assert s.aborted and s.closed
    m.poll(DT, 0.2)
    assert f.calls == 1                         # not before RETRY_S
    m.mixer._failed_at -= M.RETRY_S
    m.poll(DT, 0.3)
    settle(m)
    assert len(f.made) == 2 and m.mixer._stream is f.made[1] and m.mixer.state == "open"


def test_a_stream_whose_active_raises_is_a_stopped_one():
    """Second review 2: sounddevice raises for a dead stream when asked if
    it is active; that is "stopped", never an exception out of `poll`."""
    m, _, f = rig("shared:a.mp4")
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)

    class Dead(FakeStream):
        @property
        def active(self):
            raise OSError("PortAudioError: stream is not running")

        @active.setter
        def active(self, v):
            pass

    s.__class__ = Dead
    m.poll(DT, 0.1)                             # no raise
    assert m.mixer.failed and m.mixer._stream is None
    m.mixer._failed_at -= M.RETRY_S
    m.poll(DT, 0.2)
    settle(m)
    assert len(f.made) == 2 and m.mixer.state == "open"


def test_close_holds_its_budget_with_an_abort_that_hangs():
    """Second review 7: the abort and close run off the calling thread and
    are waited for inside the budget; `MediaState.close` hands the closer
    only what is left, so the whole stays within the budget."""
    m, _, f = rig("shared:a.mp4")
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)
    s.abort_s = 3.0
    t0 = time.monotonic()
    assert m.close(budget=1.0) is False
    took = time.monotonic() - t0
    assert took < 1.0 + 0.2, took
    assert m.mixer._stream is None and m.mixer.state == "closed"


def test_the_closer_gets_what_the_mixer_left_of_the_budget(monkeypatch):
    m, _, f = rig("shared:a.mp4")
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)
    s.abort_s = 0.3
    seen = []
    monkeypatch.setattr(m, "drain", lambda timeout: seen.append(timeout) or True)
    assert m.close(budget=1.0)
    assert len(seen) == 1 and 0.5 <= seen[0] <= 0.72, seen


def test_close_aborts_and_closes_the_stream():
    m, _, f = rig("shared:a.mp4")
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)
    assert m.close()
    assert s.aborted and s.closed and m.mixer.state == "closed" and m.mixer.voices == ()
    assert m.opener.closes == 1                 # the source's close ends its soundtrack


def test_close_returns_within_its_budget_with_an_open_stuck_and_never_leaves_it_playing():
    gate = threading.Event()
    m, _, f = rig("shared:a.mp4", gate=gate)
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    t0 = time.monotonic()
    assert m.close(budget=1.0) is False
    assert time.monotonic() - t0 < 1.2
    gate.set()                                  # the open returns after the exit
    deadline = time.monotonic() + 2.0
    while not f.made and time.monotonic() < deadline:
        time.sleep(0.01)
    time.sleep(0.05)
    assert f.made and f.made[0].aborted and f.made[0].closed
    assert m.mixer.state == "closed"
    m.poll(DT, 1.0)                             # a closed state opens nothing
    assert f.calls == 1


# ---------------------------------------------------------------- hot reload

def test_a_reload_of_the_module_keeps_the_stream_and_reaches_the_new_callback(monkeypatch):
    m, _, f = rig("shared:a.mp4", values={"shared:a.mp4": 0.5})
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    s = opened(m, f)

    # the class the live mixer had before a save: the module's own `Mixer`, an older one
    before = type("Mixer", (M.Mixer,), {"__module__": M.__name__})
    m.mixer.__class__ = before
    del m.mixer.__dict__["errors"]              # a field the saved module added
    m.poll(DT, 0.1)
    assert type(m.mixer) is M.Mixer and f.made == [s] and not s.closed
    assert m.mixer.errors == 0                  # backfilled from a fresh one's default
    seen = []
    old = M.Mixer._callback
    monkeypatch.setattr(M.Mixer, "_callback",
                        lambda self, *a: seen.append(1) or old(self, *a))
    assert np.allclose(s.pull(), 0.5) and seen == [1]


def test_a_mixer_of_another_class_is_left_as_it_is():
    m, _, _ = rig("shared:a.mp4")

    class Mine(M.Mixer):
        pass

    m.mixer.__class__ = Mine
    m.poll(DT, 0.0)
    assert type(m.mixer) is Mine


def test_a_media_state_from_before_the_mixer_gets_one():
    m, _, _ = rig("shared:a.mp4")
    del m.__dict__["mixer"]
    m.poll(DT, 0.0)
    assert isinstance(m.mixer, M.Mixer)


# ---------------------------------------------------------------- end to end

def test_a_real_clip_through_the_channel_and_the_mixer(tmp_path):
    """A synthesized clip (440 Hz left, 880 Hz right) opened by the real
    adapter: the toggle enables its soundtrack, the mixer's block at the
    playhead carries both tones at the gain, and off again lets the
    samples go."""
    from test_media_audio import _peak_hz, _until, _write_clip

    from hyperspace.media import adapters, video

    clip = _write_clip(tmp_path / "tones.mov")

    class R:
        def path(self, s):
            return clip

        def live(self, s):
            return None

    m = MediaState(R(), opener=adapters.open_source)
    f = Factory()
    m.mixer = M.Mixer(make=f)
    m.assign("a", 0, "file:" + str(clip))
    ch = m.channels["a"]
    try:
        m.poll(DT, 0.0)
        a = ch.source.audio
        assert a.status == video.OFF, "nothing read until the toggle"
        ch.play_audio, ch.gain = True, 0.5
        ch.pos = 1 / 3                          # scrub to 1 s of the 3 s clip
        m.poll(DT, 0.1)
        assert _until(lambda: a.status == video.READY)
        out = opened(m, f).pull(AUDIO_RATE // 2)
        assert _peak_hz(out[:, 0]) == pytest.approx(440.0, abs=4.0)
        assert _peak_hz(out[:, 1]) == pytest.approx(880.0, abs=4.0)
        assert np.abs(out).max() == pytest.approx(0.25, abs=0.02)
        ch.play_audio = False
        for k in range(OFF_FRAMES):
            m.poll(DT, 0.2 + k * DT)
        assert m.drain(2.0)
        assert a.status == video.OFF and a.nbytes == 0
    finally:
        assert m.close(2.0)
