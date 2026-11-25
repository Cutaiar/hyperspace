"""How often a GRAPH node's thumbnail is copied (`outputs.THUMB_HZ`): each at
25 Hz at most, spread over the frames (`PreviewTextures.due`), with nothing
dropped, dimmed or lost because a frame skipped it. The clock is pinned."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from test_unwired_thumbs import SIZE, UNWIRED, S, _renderer, _views

from hyperspace import render
from hyperspace.outputs import THUMB_HZ, THUMB_LATE_S, PreviewTextures

PIC = NS(size=(64, 36))


class Run:
    """A renderer's frames at `fps`, the page wanting the same names in each."""

    def __init__(self, fps: float, names=("a",)):
        self.t, self.fps, self.names = 100.0, fps, names
        self.th = PreviewTextures(None, lambda: self.t)
        self.copies: list[list[str]] = []
        self.shades: list[float] = []

    def frame(self, made=None, want=True, how="picture") -> list[str]:
        """One frame's end; `made(name, copied)` whether the node made a picture."""
        self.t += 1.0 / self.fps
        if want:
            self.th.want(dict.fromkeys(self.names, how))
        due = self.th.take()
        self.th.begin_frame()
        copied: list[str] = []
        for name in sorted(due):
            self.th.tried(name, due[name])
            if made is None or made(name, copied):
                self.th.put(name, PIC)
                copied.append(name)
        self.th.end_frame()
        self.copies.append(copied)
        self.shades += [self.th.shade(n) for n in self.names]
        return copied

    def run(self, seconds: float, **kw) -> Run:
        for _ in range(round(seconds * self.fps)):
            self.frame(**kw)
        return self


@pytest.mark.parametrize("fps", [30, 60, 100, 119.5, 240])
def test_each_node_is_copied_25_times_a_second_and_is_never_dimmed_between(fps):
    assert THUMB_HZ == 25.0
    r = Run(fps, tuple("abcdefg")).run(4.0)
    for n in r.names:
        got = sum(n in c for c in r.copies)
        assert 4 * 25 - 2 <= got <= 4 * 25 + 2, (n, got)
    assert set(r.shades) == {1.0} and r.th.kept == len(r.names)


@pytest.mark.parametrize("fps", [5, 12, 24])
def test_at_25_frames_a_second_or_fewer_nothing_is_skipped(fps):
    r = Run(fps, tuple("abc")).run(2.0)
    assert all(len(c) == 3 for c in r.copies)


@pytest.mark.parametrize("n", [2, 8, 15, 40])
def test_the_copies_are_spread_over_the_frames(n):
    r = Run(120.0, tuple(f"n{i}" for i in range(n))).run(2.0)
    assert len(r.copies[0]) == n                    # never copied: at once
    share = n * THUMB_HZ / 120.0
    assert max(len(c) for c in r.copies[1:]) <= share + 2.0     # never the lot at once


def test_wanted_for_the_first_time_or_found_another_way_is_copied_at_once():
    r = Run(1000.0, ("a",))
    assert r.frame() == ["a"]
    while r.frame():                                # (between two beats)
        pass
    r.names = ("a", "b")
    assert r.frame() == ["b"]
    r.names = ("a",)
    assert r.frame(how="card") == ["a"]
    r.th.drop("a")                                  # dropped, wanted again
    assert r.frame(how="card") == ["a"]


def test_a_wish_between_two_beats_is_kept_until_its_beat():
    r = Run(1000.0, ("a",))
    r.frame()
    while not r.frame():
        pass
    assert not r.frame()                            # wanted, its beat just gone …
    waits = 0
    while not r.frame(want=False):                  # … and not again
        waits += 1
        assert waits < 41
    assert r.th.wanted == {}
    for _ in range(100):
        assert not r.frame(want=False)              # copied once, not for ever


def test_a_node_that_stops_dims_and_is_lit_the_frame_it_makes_one_again():
    r = Run(120.0).run(0.5)
    r.run(THUMB_LATE_S + 2.0 / THUMB_HZ, made=lambda n, c: False)
    assert r.th.shade("a") == PreviewTextures.DIM
    r.run(1.0, made=lambda n, c: False)
    assert r.th.shade("a") == 0.0 and r.th.kept == 1
    assert r.frame() == ["a"] and r.th.shade("a") == 1.0


@pytest.mark.parametrize("fps", [27, 33, 48, 60, 120])
@pytest.mark.parametrize("names", [("cut", "mask"), ("mask", "cut")])
def test_a_mask_only_anothers_repaint_makes_is_never_dimmed(fps, names):
    """A matte the frame itself did not ask for is made when the cut's
    thumbnail paints the cut (masks are tried last): it is copied on the
    cut's beats, whatever its own."""
    r = Run(fps, names).run(4.0, made=lambda n, copied: n == "cut" or "cut" in copied)
    assert set(r.shades) == {1.0}
    assert sum("mask" in c for c in r.copies) > 4 * THUMB_HZ / 2 - 2


def test_a_failed_frame_makes_nothing_and_the_next_lights_it(ctx):
    r, views = _renderer(ctx), _views(ctx)
    t = [10.0]
    r.thumbs.clock = lambda: t[0]
    r.thumbs.want({"scene": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    assert r.thumbs.shade("scene") == 1.0
    t[0] += THUMB_LATE_S + 0.01
    r.thumbs.want({"scene": "picture"})
    r._thumb_frame = None                           # (a frame that failed before its graph)
    r._thumbnails()
    assert r.thumbs.shade("scene") == PreviewTextures.DIM
    r.thumbs.want({"scene": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    assert r.thumbs.shade("scene") == 1.0


def test_the_unwired_budget_goes_round_and_loses_no_wish(ctx):
    extra = ("grain", "bloom", "glimmer", "prism")
    r, views = _renderer(ctx, extra), _views(ctx)
    t = [10.0]
    r.thumbs.clock = lambda: t[0]
    names = ["wave", "acid", *extra]
    count = dict.fromkeys(names, 0)
    for k in range(60):
        t[0] += 1 / 60
        r.thumbs.want(dict.fromkeys(names, UNWIRED))
        r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0 + k / 60)
        assert r.thumbs.count <= render.UNWIRED_PER_FRAME
        for n in names:
            count[n] += r.thumbs.made_in.get(n) == r.thumbs.frame
        if k >= 2:                                  # (the first two frames fill in)
            assert {r.thumbs.shade(n) for n in names} == {1.0}
    assert all(24 <= c <= 27 for c in count.values()), count


def test_the_renderer_copies_a_wired_node_25_times_a_second(ctx):
    r, views = _renderer(ctx), _views(ctx)
    t = [10.0]
    r.thumbs.clock = lambda: t[0]
    n = 0
    for k in range(60):
        t[0] += 1 / 60
        r.thumbs.want({"scene": "picture", "kaleido": "picture"})
        r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0 + k / 60)
        n += r.thumbs.count
        assert r.thumbs.shade("scene") == r.thumbs.shade("kaleido") == 1.0
    assert 2 * 24 <= n <= 2 * 27
