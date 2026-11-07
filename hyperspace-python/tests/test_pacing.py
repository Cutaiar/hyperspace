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


def _rate(pacer, clock, frames=2000, swap_s=0.0) -> float:
    """fps of a loop whose swap takes `swap_s`."""
    t0 = clock.t
    for _ in range(frames):
        clock.t += swap_s
        pacer.end_frame()
    return frames / (clock.t - t0)


# ---------------------------------------------------------------- the floor

def test_a_swap_that_does_not_wait_cannot_run_the_loop_away():
    """Locked, a hidden or occluded window: the swap returns at once. This is the
    bug SC3a fixes in today's app (1,360–1,720 fps, locked)."""
    pacer, _, clock = _pacer()
    pacer.choose(["w1"], "root")
    assert 125.0 < _rate(pacer, clock) < 127.0            # 120 × 1.05


def test_a_swap_that_waits_never_meets_the_floor():
    """At the display's rate the floor adds nothing, whatever the rate."""
    pacer, _, clock = _pacer()
    pacer.choose(["w1"], "root")
    assert 119.0 < _rate(pacer, clock, swap_s=1 / 120) < 120.0
    assert clock.slept == [] or len(clock.slept) < 5     # the first frames, before it falls behind


def test_the_floor_is_the_fastest_displays_not_the_pacing_windows():
    """Measured on a window on a 60 Hz TV beside 120 Hz displays: its swap ran at
    119.5 fps, and a floor under its own 60 would have halved the loop."""
    pacer, _, clock = _pacer((60, 120, 60))
    pacer.choose(["on-the-tv"], "root")
    assert 119.0 < _rate(pacer, clock, swap_s=1 / 120) < 120.0
    pacer, _, clock = _pacer((60,))
    pacer.choose(["w1"], "root")
    assert 62.0 < _rate(pacer, clock) < 64.0


def test_no_display_live_a_timer_at_60():
    pacer, _, clock = _pacer()
    pacer.choose([], "root")
    assert pacer.owner is None
    assert 59.5 < _rate(pacer, clock) < 60.5


def test_a_display_that_will_not_say_is_a_bound_that_caps_nothing():
    pacer, g, clock = _pacer()

    def gone():
        raise RuntimeError("no monitor")

    g.get_monitors = gone
    pacer.choose(["w1"], "root")
    assert 240.0 < _rate(pacer, clock) < 260.0
    pacer, _, clock = _pacer((0,))
    pacer.choose(["w1"], "root")
    assert 240.0 < _rate(pacer, clock) < 260.0


def test_the_displays_are_looked_up_about_once_a_second():
    pacer, g, clock = _pacer()
    calls = []
    real = g.get_monitors
    g.get_monitors = lambda: (calls.append(1), real())[1]
    pacer.choose(["w1"], "root")
    _rate(pacer, clock, frames=int(3.5 * 126))
    assert 3 <= len(calls) <= 5
    # one that changes is noticed, without a restart
    g.hz = (60,)
    clock.t += pacing.REFRESH_EVERY_S
    pacer.end_frame()
    assert pacer.refresh == 60.0


def test_a_stall_is_not_paid_back_as_a_burst():
    clock = _Clock()
    floor = Floor(100.0, clock, clock.sleep)
    floor.wait()
    clock.t += 5.0
    floor.wait()               # behind by far more than a period: start again from now
    t0 = clock.t
    floor.wait()
    assert 0.009 < clock.t - t0 < 0.011


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


def test_a_handover_resets_the_floor_and_changes_its_rate():
    """No debt or credit carried over a handover (`dt` absorbs the change of rate)."""
    pacer, _, clock = _pacer()
    pacer.choose(["a"], "root")
    assert 125.0 < _rate(pacer, clock) < 127.0
    pacer.choose([], "root")
    assert pacer.floor.next >= clock.t - 1e-3
    assert 59.5 < _rate(pacer, clock) < 60.5
    pacer.choose(["c"], "root")
    assert 125.0 < _rate(pacer, clock) < 127.0
