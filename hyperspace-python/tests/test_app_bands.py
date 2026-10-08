"""Plan 22 B3: the frame hands the renderer the analyzer's lanes (`app._bands`
→ `Renderer.bands`, the face shaders' u_levels) — render input, read-only,
like the dim. It sits outside the frame's guarded step, so it must never
raise, and it must read the lanes this frame's step made, before the render
window draws. The frame's own documented order is test_app_boundary's; this
borrows its recording host and leaves that file alone.
"""

from types import SimpleNamespace

import numpy as np
from test_app_boundary import _boom, _host

from hyperspace import app
from hyperspace.bands import CEIL


class _Raising:
    @property
    def lanes(self):
        raise RuntimeError("an analyzer mid-swap")


def test_the_bands_never_raise_whatever_the_audio_is():
    lanes = np.array([0.0, CEIL / 2, CEIL])
    assert app._bands(SimpleNamespace(on=True, chain=SimpleNamespace(lanes=lanes))) == (
        0.0, 0.5, 1.0)
    for audio in (None, object(), SimpleNamespace(on=False, chain=SimpleNamespace(lanes=lanes)),
                  SimpleNamespace(on=True), SimpleNamespace(on=True, chain=None),
                  SimpleNamespace(on=True, chain=SimpleNamespace(lanes=None)),
                  SimpleNamespace(on=True, chain=_Raising()),
                  SimpleNamespace(on=True, chain=SimpleNamespace(lanes=3)),
                  SimpleNamespace(on=True, chain=SimpleNamespace(lanes=["loud"]))):
        assert app._bands(audio) == (), audio


def test_the_renderer_gets_this_frames_lanes_after_the_step_and_before_the_draw():
    log: list[str] = []
    h = _host(log)

    class Chain:                              # the lanes the step just made, read once
        @property
        def lanes(self):
            log.append("lanes")
            return np.array([CEIL, 0.0])
    h.audio.chain = Chain()
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is True
    i = log.index
    assert i("audio.step") < i("view.integrate") < i("lanes") < i("render.draw")
    assert log.count("lanes") == 1 and h.renderer.bands == (1.0, 0.0)


def test_a_raising_step_still_hands_over_the_bands_and_draws():
    log: list[str] = []
    h = _host(log)
    h.audio.chain = SimpleNamespace(lanes=np.array([CEIL]))
    h.lfos.step = _boom
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.renderer.bands == (1.0,) and log[-2:] == ["render.draw", "panel.draw"]
    h.audio.chain = _Raising()                # a missing or swapped analyzer: no bands
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert h.renderer.bands == () and "render.draw" in log
