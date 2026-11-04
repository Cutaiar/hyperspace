"""Plan 45 V4 — sync with video as master, and varispeed: the mixer's read
head, slewed toward the transport and resampled by its speed.

Deterministic, no audio device and no threads: the voices come from a real
`Transport`, stepped here, and the blocks are pulled through the callback by
hand, so the order of steps and callbacks is the test's. The soundtrack is a
ramp — each sample's value is its own place in the clip — so what comes out
*is* the read head, sample by sample, and a repeat, a skip or a click is
visible as a slope that moved."""

import tracemalloc

import numpy as np
import pytest
from test_media_mixer import Factory, opened, rig

from hyperspace.media import adapters, video
from hyperspace.media import mixer as M
from hyperspace.media.channels import MediaState
from hyperspace.media.transport import Transport
from hyperspace.media.video import AUDIO_RATE, AUDIO_WINDOW_S, Soundtrack, _Window

DT = 1 / 60
N = M.BLOCK
SCALE = 1e-6            # a ramp's value per sample: 1e6 samples before it clips (21 s)


class Ramp:
    """Sample `i` is `i × SCALE` on both sides, for i in `span`, else zeros."""

    def __init__(self, length=30 * AUDIO_RATE, start=0):
        self.start, self.length = start, length
        self.reads = []

    def holds(self, at, n):
        return self.start <= at and at + n <= self.start + self.length

    def read(self, at, n, out=None):
        self.reads.append((at, n))
        i = np.arange(at, at + n, dtype=np.float64)
        v = np.where((i >= self.start) & (i < self.start + self.length), i * SCALE, 0.0)
        block = np.stack([v, v], axis=1).astype(np.float32)
        if out is None:
            return block
        out = out[:n]
        out[:] = block
        return out


class Deck:
    """One transport, one track, one mixer; `frame` and `block` in any order."""

    def __init__(self, duration=10.0, track=None, loop="loop", gain=1.0):
        self.tr = Transport(duration)
        self.track = track if track is not None else Ramp()
        self.loop, self.gain = loop, gain
        self.rate, self.pos, self.jog = 1.0, 0.0, 0.0
        self.mx = M.Mixer(make=Factory())

    def frame(self, dt=DT):
        self.tr.step(dt, self.rate, self.pos, self.jog, self.loop)
        self.feed()

    def feed(self):
        self.mx.feed((M.Voice(self.track, self.tr.playhead, self.gain, self.tr.velocity,
                              self.tr.wrap, self.tr),), asked=False)

    def block(self, frames=N):
        out = np.full((frames, 2), 9.0, np.float32)
        self.mx._callback(out, frames, None, None)
        return out[:, 0].astype(np.float64)

    def play(self, n, rate=None):
        """`n` frames each with one block; every sample out, joined."""
        if rate is not None:
            self.rate = rate
        got = []
        for _ in range(n):
            self.frame()
            got.append(self.block())
        return np.concatenate(got)

    @property
    def head(self):
        return self.mx._live[0][1]


def places(out):
    """A ramp's output as the sample places it read."""
    return np.round(out / SCALE, 1)


# ---------------------------------------------------------------- rate 1

def test_rate_1_is_every_sample_once_in_order_and_on_the_transport():
    d = Deck()
    d.pos = d.tr.last_pos = 0.1
    d.tr.playhead = 1.0
    d.play(2)                                  # (the first block fades in)
    out = d.play(120)
    assert np.all(np.abs(np.diff(places(out)) - 1.0) < 0.5)
    assert d.head.speed == 1.0, "no trim: the head is on the transport"
    assert abs(round(d.tr.playhead * AUDIO_RATE) + N - d.head.at) <= 1


def test_rate_1_with_the_clocks_out_of_phase_repeats_and_skips_nothing():
    """What V2 could not do: a callback twice between two steps, a step with
    no callback. The samples still come out one after another."""
    d = Deck()
    d.play(3)
    got = []
    for k in range(240):
        d.frame()
        for _ in range((0, 2, 1, 1, 2, 0, 1)[k % 7]):
            got.append(d.block())
    steps = np.diff(places(np.concatenate(got)))
    assert np.all(np.abs(steps - 1.0) < 0.5), "not one repeated or skipped sample"
    assert d.head.speed == 1.0


def test_a_slower_audio_clock_is_held_in_sync_by_a_bend_too_small_to_hear():
    """The two clocks really differ: the frame's dt says 0.1 % more than the
    blocks moved. The head does not drift away: it settles at the edge of
    the dead band, trimmed, with no cut."""
    d = Deck(duration=20.0)
    d.play(2)
    got = []
    for _ in range(60 * 15):
        d.frame(DT * 1.001)
        got.append(d.block())
    err = round(d.tr.playhead * AUDIO_RATE) - d.head.at
    assert abs(err) < M.DEAD * 1.5 + N
    assert abs(d.head.speed - 1.001) < 0.002
    steps = np.diff(places(np.concatenate(got)))
    assert np.abs(steps).max() < 1.5, "no cut, nothing jumped"


# ---------------------------------------------------------------- varispeed

@pytest.mark.parametrize("rate", [2.0, 0.5, 1.5, 4.0, -1.0, -2.0, -0.5])
def test_any_rate_reads_that_many_samples_a_sample(rate):
    d = Deck(duration=20.0)
    d.pos = d.tr.last_pos = 0.5
    d.tr.playhead = 10.0
    d.rate = rate
    d.play(3)
    out = d.play(60)
    steps = np.diff(places(out))
    assert np.all(np.abs(steps - rate) < 0.5), (steps.min(), steps.max())
    assert abs(round(d.tr.playhead * AUDIO_RATE) + rate * N - d.head.at) <= 2


def test_a_rate_change_glides_inside_one_block():
    d = Deck()
    d.play(10)
    d.rate = 2.0
    d.frame()
    glide = np.diff(places(d.block()))
    assert 0.9 < glide[0] < 1.2 and 1.8 < glide[-1] < 2.1
    assert np.all(np.diff(glide) > -0.5), "the speed rises, it does not step"


def test_reverse_through_zero_speed_is_a_turn_not_a_click():
    d = Deck()
    d.pos = d.tr.last_pos = 0.5
    d.tr.playhead = 5.0
    d.play(5)
    d.rate = -1.0
    d.frame()
    turn = places(d.block())
    assert np.abs(np.diff(turn)).max() < 1.5
    assert turn[-1] < turn[N // 2], "over by the block's end: the head goes back"


def test_a_rate_past_what_a_block_may_read_is_clamped():
    d = Deck()
    d.tr.velocity = 400.0
    d.feed()
    d.block()
    assert d.head.speed == M.MAX_SPEED
    assert max(n for _, n in d.track.reads) <= len(d.mx._src)
    assert d.mx.errors == 0


def test_a_block_of_another_size_is_warmed_once():
    d = Deck()
    d.play(2)
    d.frame()
    d.block(512)
    src = d.mx._src
    d.block(512)
    assert d.mx._src is src and len(d.mx._mix) == 512 and d.mx.errors == 0


# ---------------------------------------------------------------- rate 0

def test_rate_0_is_silence_after_one_block_fading_and_reads_nothing():
    d = Deck()
    d.pos = d.tr.last_pos = 0.1
    d.tr.playhead = 1.0
    d.play(5)
    d.rate = 0.0
    d.frame()
    fade = d.block()
    assert abs(fade[0]) > 0.0 and fade[-1] == 0.0
    assert np.abs(np.diff(fade)).max() < abs(fade[0]) * 4 / N + 10 * SCALE
    seen = len(d.track.reads)
    for _ in range(10):
        d.frame()
        assert not d.block().any(), "not one sample held as DC"
    assert len(d.track.reads) == seen
    assert d.mx.playing == 0


def test_play_after_a_hold_starts_on_the_transport_and_fades_in():
    d = Deck()
    d.pos = d.tr.last_pos = 0.1
    d.tr.playhead = 1.0
    d.play(5)
    d.play(10, rate=0.0)
    held = round(d.tr.playhead * AUDIO_RATE)
    d.rate = 1.0
    d.frame()
    first = d.block()
    assert abs(first[0]) < first[-1] / 20 and d.head.level == 1.0
    assert abs(d.head.at - (held + DT * AUDIO_RATE + N / 2)) <= N, "it glided up from a stop"


def test_a_jogs_dying_coast_fades_out_with_the_speed():
    d = Deck()
    d.rate, d.jog = 0.0, 0.5
    for _ in range(30):
        d.frame()
        d.block()
    assert d.head.level == 1.0
    d.jog = 0.0
    for _ in range(600):
        d.frame()
        d.block()
        assert d.head.level <= min(2 * abs(d.tr.velocity) / M.FADE_SPEED, 1.0)
    assert d.head.level == 0.0 and not d.block().any()


# ---------------------------------------------------------------- a scrub

def test_a_far_scrub_is_a_crossfade_within_one_block_then_on_the_transport():
    d = Deck(duration=20.0)
    d.pos = d.tr.last_pos = 0.1
    d.tr.playhead = 2.0
    d.play(5)
    before = d.head.at
    d.pos = 0.5                                # 10 s: too far to be a drag
    d.frame()
    assert d.tr.velocity == 1.0, "a jump plays on at the rate"
    cut = d.block()
    want_old = (before + np.arange(N)) * SCALE * (1.0 - (np.arange(N) + 1.0) / N)
    want_new = (10.0 * AUDIO_RATE + np.arange(N)) * SCALE * ((np.arange(N) + 1.0) / N)
    np.testing.assert_allclose(cut, want_old + want_new, atol=1e-4)
    assert np.abs(np.diff(cut)).max() < 2 * 10.0 * AUDIO_RATE * SCALE / N + 1e-4
    out = d.play(5)
    assert np.all(np.abs(np.diff(places(out)) - 1.0) < 0.5)
    assert abs(round(d.tr.playhead * AUDIO_RATE) + N - d.head.at) <= 1


def test_a_scrub_at_rate_0_lands_silent():
    d = Deck(duration=20.0)
    d.rate = 0.0
    d.play(3)
    d.pos = 0.5
    d.frame()
    assert not d.block().any(), "a jump at rate 0: nothing to hear, it just moves"
    assert d.head.at == round(10.0 * AUDIO_RATE)


def test_a_drag_of_pos_reads_at_the_speed_of_the_drag():
    """An LFO on `pos`, or a hand: the transport says the drag's speed and
    the sound reads at it, like tape under a thumb, rate 0 or not."""
    d = Deck(duration=10.0)
    d.rate = 0.0
    d.pos = d.tr.last_pos = 0.2
    d.tr.playhead = 2.0
    d.play(3)
    got = []
    for _ in range(30):
        d.pos += 0.5 * DT / 10.0                # half the clip's own speed
        d.frame()
        got.append(d.block())
    assert d.tr.velocity == pytest.approx(0.5, abs=1e-6)
    steps = np.diff(places(np.concatenate(got[3:])))
    assert np.all(np.abs(steps - 0.5) < 0.5)
    assert d.head.level == 1.0
    d.frame()                                   # it rests: rate 0 again
    d.block()
    assert d.head.level == 0.0


# ---------------------------------------------------------------- slew

def test_a_small_error_slews_without_a_click_and_closes():
    d = Deck(duration=20.0)
    d.pos = d.tr.last_pos = 0.1
    d.tr.playhead = 2.0
    d.play(5)
    d.tr.playhead += 0.1                        # 100 ms: under the cut
    assert 0.1 * AUDIO_RATE < M.CUT
    got = []
    for _ in range(120):
        d.frame()
        got.append(d.block())
    steps = np.diff(places(np.concatenate(got)))
    assert steps.max() < 1.5 and steps.max() > 1.05, "it bends the pitch, and only that"
    assert steps.min() > 0.85
    err = round(d.tr.playhead * AUDIO_RATE) + N - d.head.at
    assert abs(err) <= M.DEAD + 2


def test_inside_the_dead_band_the_head_is_left_alone():
    d = Deck(duration=20.0)
    d.pos = d.tr.last_pos = 0.1
    d.tr.playhead = 2.0
    d.play(5)
    d.tr.playhead += (M.DEAD - 100) / AUDIO_RATE
    d.frame()
    d.block()
    assert d.head.speed == 1.0


def test_a_stuck_frame_thread_is_ridden_through_then_faded_not_free_run():
    d = Deck(duration=20.0)
    d.play(5)
    d.frame()
    got = []
    for _ in range(int(M.STALE_S * AUDIO_RATE / N) - 2):
        got.append(d.block())
    steps = np.diff(places(np.concatenate(got)))
    assert np.all(np.abs(steps - 1.0) < 0.5), "a hitch is ridden through on the head"
    d.block()
    d.block()
    d.block()
    assert d.head.level == 0.0 and not d.block().any()
    d.frame(M.STALE_S)                         # it comes back: on the transport, fading in
    d.block()
    assert abs(round(d.tr.playhead * AUDIO_RATE) + N - d.head.at) <= N
    assert d.head.level == 1.0


# ---------------------------------------------------------------- the loop wrap

def test_a_loop_wrap_reads_straight_through_the_seam_in_order():
    """The decision: no jump, no gap, the head modulo the loop. A clip's last
    sample is followed by its first; a clip cut to loop is seamless."""
    d = Deck(duration=1.0, track=Ramp(length=AUDIO_RATE))
    d.play(2)
    p = places(d.play(70))                      # 1.17 s of a 1 s clip: one wrap
    seam = np.flatnonzero(np.diff(p) < 0)
    assert len(seam) == 1
    assert p[seam[0]] == AUDIO_RATE - 1 and p[seam[0] + 1] == 0
    steps = np.delete(np.diff(p), seam)
    assert np.all(np.abs(steps - 1.0) < 0.5)
    assert d.mx.errors == 0


def test_reverse_reads_back_through_the_seam():
    d = Deck(duration=1.0, track=Ramp(length=AUDIO_RATE))
    d.pos = d.tr.last_pos = 0.1
    d.tr.playhead = 0.1
    d.rate = -1.0
    d.play(2)
    got = [d.play(1) for _ in range(20)]
    p = places(np.concatenate(got))
    seam = np.flatnonzero(np.diff(p) > 0)
    assert len(seam) == 1
    assert p[seam[0]] <= 1 and p[seam[0] + 1] >= AUDIO_RATE - 2


def test_the_error_is_measured_the_short_way_round_the_loop():
    """The transport just wrapped and the head has not: a full duration
    apart on paper, a block apart on the tape. No cut, no trim."""
    d = Deck(duration=1.0, track=Ramp(length=AUDIO_RATE))
    d.pos = d.tr.last_pos = 0.98
    d.tr.playhead = 0.98
    d.play(2)
    levels = []
    for _ in range(4):
        d.frame()
        d.block()
        levels.append((d.head.level, d.head.speed))
    assert d.tr.playhead < 0.1
    assert levels == [(1.0, 1.0)] * 4


def test_a_loop_shorter_than_a_fast_block_goes_round_more_than_once():
    d = Deck(duration=0.05, track=Ramp(length=round(0.05 * AUDIO_RATE)))
    d.rate = 4.0
    d.play(3)
    assert d.mx.errors == 0
    p = places(d.play(1))
    assert p.min() >= 0 and p.max() < 0.05 * AUDIO_RATE


def test_a_once_clip_parked_at_its_end_fades_and_stays_silent():
    d = Deck(duration=1.0, loop="once")
    d.pos = d.tr.last_pos = 0.99
    d.tr.playhead = 0.99
    d.play(2)
    for _ in range(5):
        d.frame()
        out = d.block()
    assert d.tr.velocity == 0.0 and d.tr.speed == 1.0
    assert not out.any() and d.mx.playing == 0


def test_a_short_clip_needs_no_prefetch_a_whole_track_wraps_on_what_it_holds():
    """The second decision. Up to `AUDIO_WINDOW_S` is held whole: the real
    `Soundtrack` wraps with no decode, holding the head the whole time."""
    st = Soundtrack("nothing.mov")
    length = AUDIO_RATE
    st._win = _Window(0, _ramp_data(0, length))
    st.duration, st.whole = 1.0, True
    assert st.duration <= AUDIO_WINDOW_S
    d = Deck(duration=1.0, track=st)
    d.pos = d.tr.last_pos = 0.9
    d.tr.playhead = 0.9
    d.play(2)
    p = places(d.play(20))
    assert p.min() == 0 and p.max() == length - 1, "over the seam, nothing lost"
    assert d.head.level == 1.0 and d.mx.errors == 0


def test_a_long_tracks_wrap_fades_out_and_back_when_the_window_arrives():
    """... a longer track has let the head go: zeros for one decode, no
    click at the window's arrival, and the head has kept up meanwhile."""
    D = 1.0
    st = Soundtrack("nothing.mov")
    length = AUDIO_RATE
    st._win = _Window(0, _ramp_data(0, round(0.5 * length)))     # the window: the first half
    d = Deck(duration=D, track=st)
    d.pos = d.tr.last_pos = 0.25
    d.tr.playhead = 0.25
    d.play(3)
    assert d.head.level == 1.0
    st._win = _Window(round(0.6 * length), _ramp_data(round(0.6 * length), round(0.4 * length)))
    # the head is at 0.25: now outside what is held
    d.frame()
    out = d.block()
    assert d.head.level == 0.0 and out[-1] == 0.0
    silent = d.play(5)
    assert not silent.any(), "a block outside the window is zeros"
    assert d.mx.errors == 0
    st._win = _Window(0, _ramp_data(0, length))                  # the decode lands
    d.frame()
    back = d.block()
    assert d.head.level == 1.0
    assert abs(back[0]) < abs(back[-1]) / 20, "it fades back in, on the transport"
    assert abs(round(d.tr.playhead * AUDIO_RATE) + N - d.head.at) <= N


def _ramp_data(start, n):
    v = (start + np.arange(n, dtype=np.float64)) * SCALE
    return np.stack([v, v], axis=1).astype(np.float32)


# ---------------------------------------------------------------- the level

def test_a_gain_move_glides_across_a_block():
    d = Deck()
    d.pos = d.tr.last_pos = 0.5
    d.tr.playhead = 5.0
    d.play(3)
    d.gain = 0.5
    d.frame()
    out = d.block()
    assert np.abs(out[1:] / out[:-1] - 1.0).max() < 0.01, "no step in the level"
    assert out[-1] == pytest.approx(0.5 * (out[0] + (N - 1) * SCALE * 0.5), rel=0.01)
    assert d.head.level == 0.5


def test_a_voice_turned_off_fades_in_one_block_and_is_let_go():
    d = Deck()
    d.pos = d.tr.last_pos = 0.5
    d.tr.playhead = 5.0
    d.play(3)
    d.mx.feed((), asked=False)
    assert d.mx.voices == () and len(d.mx._live) == 1, "one more block, to fade out"
    out = np.zeros((N, 2), np.float32)
    d.mx._callback(out, N, None, None)
    assert out[0, 0] > 0.0 and out[-1, 0] == 0.0
    d.mx.feed((), asked=False)
    assert d.mx._live == () and d.mx._heads == {}, "and nothing is kept"


def test_a_new_voice_fades_in_and_two_transports_on_one_track_read_apart():
    t = Ramp()
    a, b = Transport(10.0), Transport(10.0)
    a.playhead, b.playhead = 1.0, 5.0
    mx = M.Mixer(make=Factory())
    out = np.zeros((N, 2), np.float32)
    for _ in range(3):
        mx.feed((M.Voice(t, a.playhead, 1.0, 1.0, 0.0, a),
                 M.Voice(t, b.playhead, 1.0, 1.0, 0.0, b)), asked=False)
        mx._callback(out, N, None, None)
        a.playhead += DT
        b.playhead += DT
    heads = [h for _, h in mx._live]
    assert heads[0] is not heads[1]
    assert heads[1].at - heads[0].at == pytest.approx(4.0 * AUDIO_RATE)


# ---------------------------------------------------------------- the callback's manners

def test_the_callback_allocates_nothing_once_warm():
    """Rate 1.37 with a wrap in the block and a gain moving: the worst of
    it. Every array the callback touches is kept; python's small objects
    (a float, a view) come and go. A real `Soundtrack`: the fake allocates."""
    st = Soundtrack("nothing.mov")
    st._win = _Window(0, _ramp_data(0, AUDIO_RATE))
    d = Deck(duration=1.0, track=st)
    d.rate = 1.37
    d.play(10)
    out = np.zeros((N, 2), np.float32)
    tracemalloc.start()
    try:
        for k in range(200):
            d.gain = 0.5 + 0.5 * (k % 2)
            if k % 3 == 0:
                d.frame()               # (the frame thread's own, not the callback's)
            tracemalloc.reset_peak()
            base = tracemalloc.get_traced_memory()[0]
            d.mx._callback(out, N, None, None)
            peak = tracemalloc.get_traced_memory()[1] - base
            assert peak < N, f"{peak} bytes: a block's array would be {N * 8}"
    finally:
        tracemalloc.stop()
    assert d.mx.errors == 0


def test_the_mix_still_lands_in_the_analyzers_ring_as_it_is_heard():
    """V3 over the head: rate 2, the block in the ring is the block out, and
    a hold pushes zeros so the bands decay."""

    class Ring:
        def __init__(self):
            self.got = []

        def push(self, mono):
            self.got.append(mono.copy())

    d = Deck()
    ring = Ring()
    d.mx.listen(ring)
    d.rate = 2.0
    d.play(3)
    ring.got.clear()
    d.frame()
    out = d.block()
    np.testing.assert_allclose(ring.got[-1], out, atol=1e-7)
    assert np.abs(np.diff(places(out)) - 2.0).max() < 0.5
    d.rate = 0.0
    d.play(2)
    assert not ring.got[-1].any()


def test_through_the_channels_a_voice_is_its_transport_a_hold_included():
    m, _, _ = rig("shared:a.mp4")
    ch = m.channels["a"]
    ch.play_audio = True
    m.poll(DT, 0.0)
    v = m.mixer.voices[0]
    assert v.key is ch.transport and v.at == ch.transport.playhead and v.speed == 1.0
    assert v.wrap == ch.transport.duration                 # loop is the channel's default
    ch.rate = 0.0
    m.poll(DT, 0.1)
    assert m.mixer.voices[0].speed == 0.0 and m.mixer.voices[0].key is ch.transport
    assert m.mixer.playing == 0


def test_a_live_mixer_from_before_v4_learns_it_on_a_hot_reload():
    """The fields V4 added come from a fresh one's defaults (`Channels._mixer`),
    and a live transport has `velocity` and `wrap` from its class until it steps."""
    m, _, f = rig("shared:a.mp4", values={"shared:a.mp4": 0.5})
    m.channels["a"].play_audio = True
    m.poll(DT, 0.0)
    m.mixer.__class__ = type("Mixer", (M.Mixer,), {"__module__": M.__name__})
    for k in ("_heads", "_live", "_src", "_two", "_pos", "_pos1", "_tmp", "_idx", "_frac",
              "_ramp", "_env", "_i", "_ease"):
        del m.mixer.__dict__[k]
    m.channels["a"].transport.__dict__.pop("velocity")
    m.channels["a"].transport.__dict__.pop("wrap")
    m.poll(DT, 0.1)
    assert type(m.mixer) is M.Mixer
    s = opened(m, f)
    s.pull()
    assert np.allclose(s.pull(), 0.5) and m.mixer.errors == 0


# ---------------------------------------------------------------- the transport's side

def test_a_real_clip_at_rate_2_is_an_octave_up_and_backwards_is_the_same_tone(tmp_path):
    """Through the real adapter, the channel and the callback: 440 Hz left and
    880 Hz right in the file; the pitch follows the rate."""
    from test_media_audio import _peak_hz, _until, _write_clip

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
        ch.play_audio = True
        m.poll(DT, 0.0)
        a = ch.source.audio
        assert _until(lambda: a.status == video.READY and ch.source.duration > 0.0)
        for rate, left, right in ((2.0, 880.0, 1760.0), (-1.0, 440.0, 880.0)):
            ch.rate = rate
            m.poll(DT, 0.1)
            s = opened(m, f)
            s.pull()                            # the glide to the new rate
            m.poll(DT, 0.2)
            out = s.pull(AUDIO_RATE // 2)
            assert _peak_hz(out[:, 0]) == pytest.approx(left, abs=8.0)
            assert _peak_hz(out[:, 1]) == pytest.approx(right, abs=8.0)
        assert m.mixer.errors == 0
    finally:
        assert m.close(2.0)


def test_the_transport_says_how_it_is_really_moving():
    t = Transport(10.0)
    t.step(DT, 2.0, 0.0, 0.0, "loop")
    assert t.velocity == 2.0 and t.wrap == 10.0
    t.step(DT, -1.0, 0.0, 0.0, "once")
    assert t.velocity == -1.0 and t.wrap == 0.0
    t.reset(0.0)
    t.step(DT, -1.0, 0.0, 0.0, "once")
    assert t.velocity == 0.0, "parked at the start, pushing against it"
    t.reset(1.0)
    t.step(DT, 1.0, 1.0, 0.0, "once")
    assert t.velocity == 0.0 and t.speed == 1.0, "parked at the end"
    t.step(DT, -1.0, 1.0, 0.0, "once")
    assert t.velocity == -1.0, "and off it again"
    t.reset(0.999)
    t.step(DT, 1.0, 0.999, 0.0, "pingpong")
    assert t.direction == -1.0 and t.velocity == -1.0 and t.wrap == 0.0, "reflected"
    u = Transport(0.0)
    u.step(DT, 1.0, 0.0, 0.0, "loop")
    assert u.velocity == 0.0


def test_the_transport_tells_a_drag_from_a_jump():
    t = Transport(10.0)
    t.step(DT, 1.0, 0.0, 0.0, "loop")
    was = t.playhead
    t.step(DT, 1.0, 0.0 + was / 10.0 + 0.2 * DT, 0.0, "loop")      # 2× the clip
    assert t.velocity == pytest.approx(2.0)
    t.step(DT, 1.0, 0.9, 0.0, "loop")                               # far: the rate
    assert t.velocity == 1.0
    t.step(0.0, 1.0, 0.1, 0.0, "loop")                              # no time: a jump too
    assert t.velocity == 1.0
