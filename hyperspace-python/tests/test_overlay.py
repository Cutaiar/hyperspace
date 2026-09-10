"""Overlay mode: the window state machine, headless, against a fake backend."""

from types import SimpleNamespace

import pytest

from hyperspace.analysis import Analyser
from hyperspace.bands import Chain
from hyperspace.control import Control
from hyperspace.overlay import Overlay
from hyperspace.params import Kind, build_registry
from hyperspace.render import ViewState


class FakeBackend:
    """Records every window-system call; two monitors, window on the first."""

    def __init__(self):
        self.calls = []
        self.rect = (100, 100, 1280, 820)
        self.mons = [("Built-in", (0, 0, 1728, 1117)), ("Studio", (1728, 0, 2560, 1440))]

    def monitors(self):
        return [m[0] for m in self.mons]

    def monitor_name(self, m):
        return m

    def monitor_rect(self, m):
        return dict(self.mons)[m]

    def window_rect(self, win):
        return self.rect

    def set_rect(self, win, x, y, w, h):
        self.rect = (x, y, w, h)
        self.calls.append(("rect", (x, y, w, h)))

    def set_attrib(self, win, name, on):
        self.calls.append((name, on))

    def set_opacity(self, win, a):
        self.calls.append(("opacity", a))

    def raise_over_spaces(self, win, on):
        self.calls.append(("spaces", on))


@pytest.fixture()
def rig():
    chain = Chain(Analyser())
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain))
    b = FakeBackend()
    shown = {"panel": True}
    ov = Overlay("win", b, on_enter=lambda: shown.update(panel=False),
                 on_leave=lambda: shown.update(panel=True))
    ov.register(reg)
    return SimpleNamespace(reg=reg, ov=ov, b=b, shown=shown)


def test_params_registered(rig):
    r = rig.reg
    assert r["overlay.on"].kind is Kind.TOGGLE
    assert r["overlay.bg"].kind is Kind.CONTINUOUS
    assert r["overlay.monitor"].names == ["Built-in", "Studio"]
    assert r["overlay.bg"].text() == "clear"


def test_nothing_happens_until_apply(rig):
    rig.ov.apply()
    assert ("spaces", True) not in rig.b.calls
    assert rig.b.calls == [("MOUSE_PASSTHROUGH", False), ("opacity", 1.0)]  # off: clickable


def test_enter_covers_the_windows_monitor_and_hides_panel(rig):
    rig.reg["overlay.on"].set(True)
    rig.ov.apply()
    c = rig.b.calls
    assert ("DECORATED", False) in c and ("FLOATING", True) in c and ("spaces", True) in c
    assert rig.b.rect == (0, 0, 1728, 1117)
    assert rig.shown["panel"] is False
    assert rig.ov.bg_alpha == 0.0


def test_leave_restores_everything(rig):
    rig.reg["overlay.on"].set(True)
    rig.ov.apply()
    rig.b.calls.clear()
    rig.reg["overlay.on"].set(False)
    rig.ov.apply()
    c = rig.b.calls
    assert ("spaces", False) in c and ("FLOATING", False) in c and ("DECORATED", True) in c
    assert rig.b.rect == (100, 100, 1280, 820)
    assert rig.shown["panel"] is True
    assert rig.ov.bg_alpha == 1.0


def test_passthrough_defaults_on_but_only_applies_while_on(rig):
    assert rig.ov.passthrough is True
    rig.ov.apply()
    assert ("MOUSE_PASSTHROUGH", True) not in rig.b.calls
    rig.reg["overlay.on"].set(True)
    rig.ov.apply()
    assert ("MOUSE_PASSTHROUGH", True) in rig.b.calls
    rig.b.calls.clear()
    rig.reg["overlay.on"].set(False)
    rig.ov.apply()
    assert ("MOUSE_PASSTHROUGH", False) in rig.b.calls


def test_bg_and_alpha(rig):
    rig.reg["overlay.bg"].set_norm(0.5)
    rig.reg["overlay.alpha"].set_norm(0.25)
    rig.ov.apply()
    assert rig.ov.bg_alpha == 1.0  # off: opaque, opacity untouched
    assert ("opacity", 0.25) not in rig.b.calls
    rig.reg["overlay.on"].set(True)
    rig.ov.apply()
    assert rig.ov.bg_alpha == pytest.approx(0.5)
    assert ("opacity", 0.25) in rig.b.calls
    rig.b.calls.clear()
    rig.ov.apply()
    assert rig.b.calls == []  # change-gated: a quiet frame sends nothing


def test_monitor_switch_while_on(rig):
    rig.reg["overlay.on"].set(True)
    rig.ov.apply()
    rig.reg["overlay.monitor"].set(1)
    rig.ov.apply()
    assert rig.b.rect == (1728, 0, 2560, 1440)


def test_headless_overlay_still_tracks_enter_leave():
    chain = Chain(Analyser())
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain))
    seen = []
    ov = Overlay(None, None, on_enter=lambda: seen.append("in"),
                 on_leave=lambda: seen.append("out"))
    ov.register(reg)
    reg["overlay.on"].toggle()
    ov.apply()
    reg["overlay.on"].toggle()
    ov.apply()
    assert seen == ["in", "out"]
    assert reg["overlay.monitor"].names == ["screen"]
