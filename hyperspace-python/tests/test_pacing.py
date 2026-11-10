"""What paces the loop (SC3a, `hyperspace/pacing.py`), over a stand-in window
system and clock. tests/test_root_frame.py runs the real thing."""

from __future__ import annotations

from types import SimpleNamespace

from hyperspace import pacing
from hyperspace.pacing import Floor, Pacer


class _Clock:
    """A clock a sleep moves; a spin moves it a little, so a spin ends."""

    def __init__(self):
        self.t = 100.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        self.t += 1e-5
        return self.t

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.t += s


class _Glfw:
    def __init__(self, hz=(120, 60)):
        self.log: list[str] = []
        self.hz = hz

    def make_context_current(self, win):
        self.log.append(f"current {win}")

    def swap_interval(self, n):
        self.log.append(f"interval {n}")

    def get_monitors(self):
        return list(self.hz)

    def get_video_mode(self, mon):
        return SimpleNamespace(refresh_rate=mon)


def _pacer(hz=(120, 60)):
    clock, g = _Clock(), _Glfw(hz)
    return Pacer(g, clock, clock.sleep), g, clock


def _rate(pacer, clock, frames=2000, swap_s=0.0, swapped=True) -> float:
    """fps of a loop whose swap takes `swap_s`."""
    t0 = clock.t
    for _ in range(frames):
        clock.t += swap_s
        if swapped:
            pacer.swapped()
        pacer.end_frame()
    return frames / (clock.t - t0)


# ---------------------------------------------------------------- the floor

def test_a_swap_that_does_not_wait_cannot_run_the_loop_away():
    """Locked, a hidden or occluded window: the swap returns at once. This is the
    bug SC3a fixes in today's app (1,360–1,720 fps, locked)."""
    pacer, _, clock = _pacer()
    pacer.choose(["w1"], "root")
    assert 235.0 < _rate(pacer, clock) < 245.0


def test_a_healthy_loop_never_waits_however_uneven():
    """The gate's shape, and the review's: a real 120 Hz loop has frames of 1 ms
    beside frames of 16. None of them may wait, whatever the displays say."""
    for hz in ((120, 60), (60,), (60, 60), (0,)):
        pacer, _, clock = _pacer(hz)
        pacer.choose(["w1"], "root")
        for k in range(4000):
            clock.t += (0.001, 0.001, 0.001, 0.030)[k % 4]     # 13 ms on average, bursts of 3
            pacer.swapped()
            pacer.end_frame()
        assert clock.slept == [], hz
    # a burst up to `BURST`, at once, the same
    pacer, _, clock = _pacer()
    pacer.choose(["w1"], "root")
    clock.t += 1.0
    for _ in range(pacing.BURST - 1):
        clock.t += 0.0005
        pacer.swapped()
        pacer.end_frame()
    assert clock.slept == []


def test_the_floor_believes_no_displays_refresh():
    """Row 782: `get_video_mode` doesn't decide the swap's rate. A 120 fps loop on
    displays saying 60, 0 or nothing stays at 120, and they aren't even asked."""
    for hz in ((60,), (0,), (60, 60)):
        pacer, g, clock = _pacer(hz)
        g.get_video_mode = None
        pacer.choose(["on-the-tv"], "root")
        assert 119.0 < _rate(pacer, clock, swap_s=1 / 120) < 120.5


def test_no_display_live_a_timer_at_60():
    pacer, _, clock = _pacer()
    pacer.choose([], "root")
    assert pacer.owner is None
    assert 59.5 < _rate(pacer, clock) < 60.5


def test_no_display_connected_with_windows_alive_a_timer_at_60():
    """Clamshell with the windows still open: nothing can wait, and this is the runaway
    the floor is for."""
    pacer, _, clock = _pacer(())
    pacer.choose(["w1"], "root")
    assert 59.5 < _rate(pacer, clock) < 60.5


def test_a_frame_that_swapped_nothing_is_on_the_timer():
    """A raising draw holds the window on its last frame: no swap to wait on."""
    pacer, _, clock = _pacer()
    pacer.choose(["w1"], "root")
    assert 59.5 < _rate(pacer, clock, swapped=False) < 60.5


def test_a_window_system_that_will_not_say_caps_nothing_real():
    pacer, g, clock = _pacer()

    def gone():
        raise RuntimeError("no monitor")

    g.get_monitors = gone
    pacer.choose(["w1"], "root")
    assert 235.0 < _rate(pacer, clock) < 245.0


def test_the_displays_are_counted_about_once_a_second():
    pacer, g, clock = _pacer()
    calls = []
    real = g.get_monitors
    g.get_monitors = lambda: (calls.append(1), real())[1]
    pacer.choose(["w1"], "root")
    _rate(pacer, clock, frames=int(3.5 * 240))
    assert 3 <= len(calls) <= 5
    # displays going are noticed, without a restart
    g.hz = ()
    clock.t += pacing.LOOK_EVERY_S
    pacer.swapped()
    pacer.end_frame()
    assert pacer.displays is False


def test_a_stall_is_not_paid_back_as_a_burst():
    clock = _Clock()
    floor = Floor(100.0, clock, clock.sleep)
    floor.wait()
    clock.t += 5.0
    for _ in range(pacing.BURST):
        floor.wait()
    t0 = clock.t
    floor.wait()               # the stall earned `BURST`, no more
    assert 0.008 < clock.t - t0 < 0.012


def test_a_wait_only_sleeps():
    """No spin: the states the floor bounds are the ones meant to be quiet, and a spin
    takes the GIL from the threads that have work. The clock is read once a wait."""
    clock = _Clock()
    floor = Floor(100.0, clock, clock.sleep)
    reads: list = []
    floor.clock = lambda: (reads.append(1), clock())[1]
    for _ in range(pacing.BURST + 3):
        floor.wait()
    assert len(reads) == pacing.BURST + 3 and clock.slept


# ---------------------------------------------------------------- the handover

def test_the_first_live_window_paces_and_the_old_one_stops_waiting():
    """Between frames: interval 0 on the old pacer if it is alive, 1 on the new,
    the given window current after."""
    pacer, g, _ = _pacer()
    assert pacer.choose(["a", "b"], "root") is True
    assert g.log == ["current a", "interval 1", "current root"] and pacer.owner == "a"
    g.log.clear()
    assert pacer.choose(["a", "b"], "root") is False     # no change: no GL touched
    assert g.log == []
    assert pacer.choose(["b", "a"], "root") is True
    assert g.log == ["current a", "interval 0", "current b", "interval 1", "current root"]


def test_a_window_already_gone_is_not_touched():
    """A destroyed window can't be made current: SC3b hands over after closing."""
    pacer, g, _ = _pacer()
    pacer.choose(["a", "b"], "root")
    g.log.clear()
    pacer.choose(["b"], "root")
    assert g.log == ["current b", "interval 1", "current root"] and pacer.owner == "b"
    g.log.clear()
    pacer.choose([], "root")
    assert g.log == ["current root"] and pacer.owner is None


def test_a_handover_resets_the_floor_and_the_rate_follows():
    """No debt or credit carried over a handover (`dt` absorbs the change of rate)."""
    pacer, _, clock = _pacer()
    pacer.choose(["a"], "root")
    assert 235.0 < _rate(pacer, clock) < 245.0
    pacer.choose([], "root")
    assert pacer.floor.tokens == float(pacing.BURST)
    assert 59.5 < _rate(pacer, clock) < 60.5
    pacer.choose(["c"], "root")
    assert 235.0 < _rate(pacer, clock) < 245.0
