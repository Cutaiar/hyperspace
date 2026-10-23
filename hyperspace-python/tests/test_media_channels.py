"""Plan 32 T5 — the eight media channels (hyperspace/media/channels.py).

A `FakeOpener` stands in for `adapters.open_source`: it counts what it
opens and closes, and a fake may run a thread of its own (named
``media-fake-…``) so a leak shows in `threading.enumerate()`. The resolver
is a dict of the ids "on this Mac"."""

import threading
from pathlib import Path

import numpy as np
import pytest

from hyperspace.media import channels
from hyperspace.media.channels import BIN, CHANNELS, FITS, MediaState
from hyperspace.media.frame import MediaFrame
from hyperspace.media.source import MISSING, READY


def _frame(n: int = 0) -> MediaFrame:
    return MediaFrame(np.zeros((2, 2, 4), np.uint8), float(n), n)


class FakeSource:
    def __init__(self, sid, opener, *, timed=False, duration=0.0, kind="still",
                 thread=False):
        self.sid, self.opener = sid, opener
        self.kind, self.timed, self.duration = kind, timed, duration
        self.status = READY
        self.frame = _frame()
        self.wants: list[float] = []
        self.thread = thread
        self._t = None
        self._stop = threading.Event()

    def open(self):
        self.opener.opens += 1
        if self.thread:
            self._t = threading.Thread(target=self._stop.wait, name=f"media-fake-{self.sid}",
                                       daemon=True)
            self._t.start()

    def close(self):
        self.opener.closes += 1
        self._stop.set()
        if self._t is not None:
            self._t.join()
            self._t = None

    def latest(self):
        return self.frame

    def want(self, t):
        self.wants.append(t)


class FakeOpener:
    """`adapters.open_source` over a resolver: an id the resolver lacks is a
    `MissingSource`, as the real one does."""

    def __init__(self, **kw):
        self.kw = kw
        self.opens = self.closes = 0
        self.made: list[FakeSource] = []

    def __call__(self, sid, resolver):
        from hyperspace.media.adapters import MissingSource
        if resolver.path(sid) is None and resolver.live(sid) is None:
            return MissingSource(sid)
        s = FakeSource(sid, self, **self.kw)
        self.made.append(s)
        return s


class Here:
    """A resolver: `files` are the ids on this Mac."""

    def __init__(self, *files, live=None):
        self.files = set(files)
        self.feeds = live or {}

    def path(self, sid):
        return Path("/x") / sid if sid in self.files else None

    def live(self, sid):
        return self.feeds.get(sid)


def state(*files, **kw):
    op = FakeOpener(**kw)
    return MediaState(Here(*files), opener=op), op


def test_shape():
    assert CHANNELS == "abcdefgh" and BIN == 16 and FITS == ("cover", "contain", "stretch")
    m, _ = state()
    assert list(m.channels) == list(CHANNELS)
    ch = m.channels["a"]
    assert ch.name == "a" and ch.bin == [None] * BIN
    assert (ch.slot, ch.fit, ch.rate, ch.pos, ch.jog, ch.loop) == (0.0, 0, 1.0, 0.0, 0.0, 0)
    assert ch.source is None and ch.transport is None


def test_slot_switches_source():
    m, op = state("shared:x.png", "shared:y.png")
    m.assign("a", 0, "shared:x.png")
    m.assign("a", 1, "shared:y.png")
    m.poll(1 / 60, 0.0)
    x = m.channels["a"].source
    assert x.sid == "shared:x.png" and (op.opens, op.closes) == (1, 0)
    assert m.frame("a") is x.frame and m.status("a") == READY
    m.channels["a"].slot = 1.0
    m.poll(1 / 60, 0.1)
    y = m.channels["a"].source
    assert y.sid == "shared:y.png" and (op.opens, op.closes) == (2, 1)
    m.poll(1 / 60, 0.2)                     # unchanged: nothing reopened
    assert m.channels["a"].source is y and op.opens == 2
    m.channels["a"].slot = 0.6              # rounds to 1: still y
    m.poll(1 / 60, 0.3)
    assert m.channels["a"].source is y


def test_rapid_switching_balances():
    m, op = state("shared:x.png", "shared:y.png", thread=True)
    m.assign("a", 0, "shared:x.png")
    m.assign("a", 1, "shared:y.png")
    for k in range(500):
        m.channels["a"].slot = float(k % 2)
        m.poll(1 / 60, k / 60)
        alive = [t for t in threading.enumerate() if t.name.startswith("media-fake-")]
        assert len(alive) <= 1
    assert op.opens - op.closes == 1
    m.close()
    assert op.opens == op.closes
    assert not [t for t in threading.enumerate() if t.name.startswith("media-fake-")]


def test_empty_entry_and_missing_are_black():
    m, op = state()
    m.poll(1 / 60, 0.0)
    assert m.frame("a") is None and m.status("a") == "empty" and op.opens == 0
    m.assign("a", 0, "local:gone.png")
    m.poll(1 / 60, 0.1)
    assert m.frame("a") is None and m.status("a") == MISSING
    assert m.playhead("a") is None


def test_missing_file_appears_and_a_present_one_goes():
    """Review focus 1: a file the resolver did not have (the folder had not
    scanned yet) is opened once it has; one that goes is black and
    `missing`; a replaced one (a new stamp) reopens. Nothing raises."""
    here = Here()
    here.stamps = {}
    here.stamp = lambda sid: here.stamps.get(sid)
    op = FakeOpener()
    m = MediaState(here, opener=op)
    m.assign("a", 0, "shared:x.png")
    m.poll(1 / 60, 0.0)
    assert m.status("a") == MISSING
    here.files.add("shared:x.png")
    m.poll(1 / 60, 0.1)                       # within the recheck: not yet
    assert m.status("a") == MISSING
    m.poll(1 / 60, channels.RECHECK_S + 0.1)
    assert m.status("a") == READY and op.opens == 1
    here.stamps["shared:x.png"] = 2.0          # replaced on disk
    m.poll(1 / 60, 2 * channels.RECHECK_S + 0.2)
    assert op.opens == 2 and op.closes == 1 and m.status("a") == READY
    here.files.discard("shared:x.png")         # deleted
    m.poll(1 / 60, 3 * channels.RECHECK_S + 0.3)
    assert m.frame("a") is None and m.status("a") == MISSING and op.opens == op.closes


def test_transport_drives_want():
    m, _ = state("shared:clip.mp4", timed=True, duration=10.0, kind="video")
    m.assign("a", 0, "shared:clip.mp4")
    m.channels["a"].rate = 2.0
    for k in range(30):
        m.poll(1 / 30, k / 30)
    src = m.channels["a"].source
    assert src.wants[-1] == pytest.approx(2.0, abs=1e-6)
    sec, dur = m.playhead("a")
    assert sec == pytest.approx(2.0, abs=1e-6) and dur == 10.0


def test_duration_known_late_starts_at_pos():
    """A video's duration is probed on its thread: until then the transport
    runs on 0 s; once known, the playhead starts where `pos` says."""
    m, _ = state("shared:clip.mp4", timed=True, duration=0.0, kind="video")
    m.assign("a", 0, "shared:clip.mp4")
    m.channels["a"].pos = 0.5
    m.poll(1 / 60, 0.0)
    src = m.channels["a"].source
    src.duration = 8.0
    m.channels["a"].rate = 0.0
    m.poll(1 / 60, 0.1)
    assert src.wants[-1] == pytest.approx(4.0)


def test_live_freeze_at_rate_zero():
    feed = None
    op = FakeOpener(kind="camera")
    m = MediaState(Here(live={"camera:cam": object()}), opener=op)
    m.assign("a", 0, "camera:cam")
    m.poll(1 / 60, 0.0)
    feed = m.channels["a"].source
    first = feed.frame
    assert m.frame("a") is first
    m.channels["a"].rate = 0.0
    m.poll(1 / 60, 0.1)
    feed.frame = _frame(5)                     # the feed moves on
    m.poll(1 / 60, 0.2)
    assert m.frame("a") is first               # frozen
    m.channels["a"].rate = 1.0
    m.poll(1 / 60, 0.3)
    assert m.frame("a") is feed.frame          # live again


def test_gl_poll_is_read_when_a_source_has_it():
    m, _ = state("syphon:app/s")
    m.resolver.feeds["syphon:app/s"] = object()
    m.assign("a", 0, "syphon:app/s")
    m.poll(1 / 60, 0.0)
    src = m.channels["a"].source
    gpu = MediaFrame(None, 0.0, 1, texture=7, tex_size=(4, 4))
    src.gl_poll = lambda: gpu
    assert m.frame("a") is gpu


def test_missing_lists_local_ids():
    m, _ = state("shared:y.png")
    m.assign("a", 0, "local:x.png")
    m.assign("b", 3, "shared:y.png")
    m.assign("c", 0, "local:x.png")            # listed once
    assert m.missing() == ["local:x.png"]
    # a live id is asked of the resolver too: no feed, listed; a feed, not
    m.assign("e", 0, "camera:FaceTime HD Camera")
    assert m.missing() == ["local:x.png", "camera:FaceTime HD Camera"]
    m.resolver.feeds["camera:FaceTime HD Camera"] = object()
    assert m.missing() == ["local:x.png"]


def test_close_closes_all():
    m, op = state("shared:x.png", "shared:y.png", thread=True)
    for c in "abc":
        m.assign(c, 0, "shared:x.png")
    m.assign("d", 0, "shared:y.png")
    m.poll(1 / 60, 0.0)
    assert op.opens == 4
    m.close()
    assert op.closes == 4
    assert all(ch.source is None for ch in m.channels.values())
    assert not [t for t in threading.enumerate() if t.name.startswith("media-fake-")]
    m.poll(1 / 60, 0.1)                        # a stray frame after close opens nothing
    assert op.opens == 4


def test_a_source_that_raises_on_open_is_an_error_not_a_crash():
    class Bad(FakeSource):
        def open(self):
            raise OSError("no")
    m = MediaState(Here("shared:x.png"), opener=lambda sid, r: Bad(sid, FakeOpener()))
    m.assign("a", 0, "shared:x.png")
    m.poll(1 / 60, 0.0)
    assert m.status("a").startswith("error:") and m.frame("a") is None


def test_bins_json_round_trip_and_bad_ids():
    m, _ = state()
    m.assign("a", 0, "shared:loops/tunnel.mp4")
    m.assign("a", 2, "camera:FaceTime HD Camera")
    m.assign("h", 15, "local:x.png")
    doc = m.to_json()
    assert doc == {"channels": {"a": ["shared:loops/tunnel.mp4", None,
                                      "camera:FaceTime HD Camera"],
                                "h": [None] * 15 + ["local:x.png"]}}
    n, _ = state()
    assert n.from_json(doc) == []
    assert n.to_json() == doc
    notes = n.from_json({"channels": {"a": ["nope", "shared:ok.png", 3],
                                      "z": ["shared:x.png"],
                                      "b": ["shared:b.png"] * 17}})
    assert n.channels["a"].bin[:3] == [None, "shared:ok.png", None]
    assert n.channels["b"].bin == ["shared:b.png"] * 16
    assert n.channels["h"].bin == [None] * 16   # a load replaces every bin
    assert len(notes) == 4 and any("'nope'" in s for s in notes)
    assert n.from_json({}) == [] and n.to_json() == {"channels": {}}
