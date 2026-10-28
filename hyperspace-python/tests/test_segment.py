"""Plan 39 T4 — the segment worker (segment.py): a person matte off the
frame thread, on the dream worker's pattern.

The worker with a fake backend: `submit` never blocks and the latest wins
(a frame still waiting is dropped for the newer, and counted); `latest()`
is the newest matte, its index and its size; an error is caught and said,
and the next good result clears it; the thread sleeps until a submit and
`close()` joins within a second. `pick_backend` with a missing library is
a reason string, never an exception; a backend that will not open is said.
The real backends — Apple Vision and torchvision's LR-ASPP — run once each
on a synthetic frame in the `live` tier (`pytest --all`), never on a
camera."""

from __future__ import annotations

import sys
import threading
import time

import numpy as np
import pytest

from hyperspace import segment


class Gate(segment.Backend):
    """A backend that holds each run until let go, and counts its calls."""

    name = "gate"

    def __init__(self, fail_on: set[int] | None = None):
        self.go = threading.Event()
        self.started = threading.Event()
        self.seen: list[int] = []
        self.opened = self.closed = 0
        self.fail_on = fail_on or set()

    def open(self) -> None:
        self.opened += 1

    def run(self, frame, quality="fast"):
        self.started.set()
        assert self.go.wait(5.0)
        v = int(frame[0, 0, 0])
        self.seen.append(v)
        if v in self.fail_on:
            raise RuntimeError(f"bad frame {v}")
        h, w = frame.shape[:2]
        return np.full((h // 2, w // 2), v, np.uint8)

    def close(self) -> None:
        self.closed += 1


def _frame(v: int, w: int = 8, h: int = 6) -> np.ndarray:
    return np.full((h, w, 4), v, np.uint8)


def test_latest_wins_and_drops_are_counted():
    b = Gate()
    w = segment.SegmentWorker(b, name="t")
    try:
        assert w.latest() is None and w.said() == "waiting for gate fast"
        w.submit(_frame(1), 1)
        assert b.started.wait(2.0)           # 1 is running …
        w.submit(_frame(2), 2)                # … 2 waits …
        assert not w.wants()
        w.submit(_frame(3), 3)                # … and is dropped for 3
        assert w.drops == 1
        b.go.set()
        assert w.drain()
        assert b.seen == [1, 3]
        mask, index, size = w.latest()
        assert index == 3 and size == (4, 3) and mask.shape == (3, 4) and (mask == 3).all()
        assert w.results == 2 and b.opened == 1
        assert w.said().startswith("4×3 · gate fast · a frame or two late · ")
    finally:
        w.close()


def test_submit_copies_the_frame_and_never_waits():
    b = Gate()
    w = segment.SegmentWorker(b)
    try:
        f = _frame(5)
        t0 = time.perf_counter()
        w.submit(f, 1)
        f[...] = 9                             # the caller's array is its own again
        assert time.perf_counter() - t0 < 0.05
        b.go.set()
        assert w.drain()
        assert b.seen == [5]
        # (a rows-reversed view — the readback's — is copied as it reads)
        w.submit(_frame(7)[::-1], 2)
        assert w.drain() and b.seen[-1] == 7
    finally:
        w.close()


def test_an_error_is_said_and_the_next_result_clears_it():
    b = Gate(fail_on={2})
    b.go.set()
    w = segment.SegmentWorker(b)
    try:
        w.submit(_frame(2), 1)
        assert w.drain()
        assert w.errors == 1 and "bad frame 2" in w.error
        assert w.said() == "gate: RuntimeError: bad frame 2"
        assert w.alive                         # the worker outlives a bad frame
        w.submit(_frame(4), 2)
        assert w.drain()
        assert w.error == "" and w.latest()[1] == 2
    finally:
        w.close()


def test_a_backend_that_will_not_open_is_said():
    class Broken(segment.Backend):
        name = "broken"

        def open(self):
            raise ImportError("no such framework")

    w = segment.SegmentWorker(Broken())
    try:
        w.submit(_frame(1), 1)
        assert w.drain()
        assert w.said() == "broken: broken would not open: ImportError: no such framework"
        assert w.latest() is None
    finally:
        w.close()


def test_the_thread_sleeps_until_a_submit_and_close_joins_within_a_second():
    b = Gate()
    b.go.set()
    w = segment.SegmentWorker(b, name="sleepy")
    assert w._thread.name == "segment-sleepy"
    time.sleep(0.05)
    assert b.opened == 0 and b.seen == []     # nothing submitted: nothing opened or run
    t0 = time.perf_counter()
    w.close()
    assert time.perf_counter() - t0 < segment.CLOSE_S
    assert not w.alive
    w.submit(_frame(1), 1)                     # closed: a submit is ignored
    assert w.latest() is None
    # … and one closed mid-run is joined within the second too
    b2 = Gate()
    w2 = segment.SegmentWorker(b2)
    w2.submit(_frame(1), 1)
    assert b2.started.wait(2.0)
    t0 = time.perf_counter()
    w2.close()
    assert time.perf_counter() - t0 < segment.CLOSE_S + 0.1
    b2.go.set()


def test_a_reason_string_is_a_worker_that_makes_nothing_and_says_why():
    w = segment.SegmentWorker("Vision is not installed")
    assert not w.alive and not w.wants()
    w.submit(_frame(1), 1)
    assert w.latest() is None and w.said() == "Vision is not installed"
    w.close()


def test_pick_backend_says_a_missing_library_in_words(monkeypatch):
    monkeypatch.setattr(segment, "_have", lambda m: False)
    assert segment.pick_backend({"backend": "vision"}) == segment.VISION_MISSING
    assert segment.pick_backend({"backend": "torch"}) == segment.TORCH_MISSING
    assert segment.pick_backend({}) == segment.TORCH_MISSING      # auto, nothing there
    assert "one of" in segment.pick_backend({"backend": "coreml"})
    monkeypatch.setattr(segment, "_have", lambda m: True)
    assert isinstance(segment.pick_backend({"backend": "torch"}), segment.TorchBackend)
    assert isinstance(segment.pick_backend({"backend": "vision"}), segment.VisionBackend)
    auto = segment.pick_backend({"backend": "auto"})
    assert isinstance(auto, segment.VisionBackend if sys.platform == "darwin"
                      else segment.TorchBackend)
    # (found, not loaded: picking imports nothing)
    w = segment.make_worker({"backend": "vision"}, "segment.2")
    assert w.name == "segment.2" and w.backend_name == "Vision"
    w.close()


def test_the_levels_and_the_input_sizes():
    assert segment.quality_of(0) == "fast" and segment.quality_of(2) == "accurate"
    assert segment.quality_of("balanced") == "balanced" and segment.quality_of(9) == "fast"
    v, t = segment.VisionBackend(), segment.TorchBackend()
    assert v.input_size("fast", (1280, 720)) == (640, 360)
    assert v.input_size("accurate", (640, 360)) == (640, 360)     # never larger
    assert t.input_size("fast", (1280, 720)) == (427, 240)
    assert t.input_size("accurate", (320, 240)) == (320, 240)
    assert segment.aspect_size(256, (1280, 720)) == (256, 144)
    m = np.zeros((192, 256), np.uint8)
    m[:96] = 255
    r = segment.resample(m, (256, 144))
    assert r.shape == (144, 256) and r[10, 10] == 255 and r[130, 10] == 0


# ---------------------------------------------------------------- the real backends, once each

def _synthetic(w: int = 640, h: int = 360) -> np.ndarray:
    """A synthetic frame — a light figure-ish block on a dark ground — never a camera's."""
    f = np.full((h, w, 4), 30, np.uint8)
    f[..., 3] = 255
    f[h // 6: h, w // 3: 2 * w // 3, :3] = 200
    return f


@pytest.mark.live
@pytest.mark.skipif(sys.platform != "darwin", reason="Apple Vision is macOS only")
def test_vision_runs_once_on_a_synthetic_frame():
    b = segment.pick_backend({"backend": "vision"})
    assert isinstance(b, segment.VisionBackend), b
    w = segment.SegmentWorker(b)
    try:
        w.submit(_synthetic(), 1)
        assert w.drain(30.0)
        assert w.error == "", w.error
        mask, index, size = w.latest()
        # fast is 256×192 from Vision, resampled to the frame's 16:9
        assert index == 1 and size == (256, 144) and mask.shape == (144, 256)
        assert mask.dtype == np.uint8 and 0 <= int(mask.min()) <= int(mask.max()) <= 255
        assert w.said().startswith("256×144 · Vision fast")
    finally:
        w.close()


@pytest.mark.live
def test_torch_runs_once_on_a_synthetic_frame():
    b = segment.pick_backend({"backend": "torch"})
    assert isinstance(b, segment.TorchBackend), b
    w = segment.SegmentWorker(b)
    try:
        w.submit(_synthetic(), 1)
        assert w.drain(120.0)
        assert w.error == "", w.error
        mask, index, size = w.latest()
        assert index == 1 and size == (427, 240) and mask.shape == (240, 427)
        assert mask.dtype == np.uint8 and 0 <= int(mask.min()) <= int(mask.max()) <= 255
        # a second worker shares the one model
        b2 = segment.TorchBackend()
        b2.open()
        assert b2.net is b.net
    finally:
        w.close()
