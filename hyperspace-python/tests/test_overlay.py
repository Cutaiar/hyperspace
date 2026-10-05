"""Output settings: the render window's state machine, headless, against a fake backend."""

from types import SimpleNamespace

import pytest

from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.overlay import Output
from hyperspace.params import Kind, build_registry
from hyperspace.view import ViewState


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

    def set_fullscreen(self, win, m):
        self.rect = self.monitor_rect(m)
        self.calls.append(("fullscreen", m))

    def set_windowed(self, win, x, y, w, h):
        self.rect = (x, y, w, h)
        self.calls.append(("windowed", (x, y, w, h)))

    def set_attrib(self, win, name, on):
        self.calls.append((name, on))

    def set_opacity(self, win, a):
        self.calls.append(("opacity", a))

    def raise_over_spaces(self, win, on):
        self.calls.append(("spaces", on))


def _registry():
    chain = Analyzer(Analyser())
    return build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain))


@pytest.fixture()
def rig():
    reg = _registry()
    b = FakeBackend()
    out = Output("win", b, allowed=True)   # [output] overlay = true: the tests of overlay itself
    out.register(reg)
    return SimpleNamespace(reg=reg, out=out, b=b)


# ---- params ----

def test_params_registered(rig):
    r = rig.reg
    assert r["output.fullscreen"].kind is Kind.TOGGLE
    assert r["output.overlay"].kind is Kind.TOGGLE
    assert r["output.passthrough"].kind is Kind.TOGGLE
    assert r["output.bg"].kind is Kind.CONTINUOUS
    assert r["output.alpha"].kind is Kind.CONTINUOUS
    assert r["output.monitor"].kind is Kind.ENUM
    assert r["output.monitor"].names == ["follow window", "Built-in", "Studio"]
    assert r["output.bg"].text() == "clear"
    assert all(p.group == "output" for p in r.group("output"))


def test_rig_settings_never_persist_or_modulate(rig):
    r = rig.reg
    for pid in ("output.monitor", "output.fullscreen", "output.overlay", "output.passthrough"):
        assert not r[pid].persist, pid
        assert not r[pid].modulatable, pid
    # ground and opacity are a look: a preset keeps them, a lane may drive them
    for pid in ("output.bg", "output.alpha"):
        assert r[pid].persist and r[pid].modulatable, pid
    saved = r.snapshot("output")
    assert set(saved) == {"output.bg", "output.alpha"}


def test_dim_is_a_rig_setting_that_starts_bright(rig):
    """Plan 15 WP3 (decision 28): the master dim is the operator's — 1 on a
    fresh Output whatever the config says (there is no key), never saved,
    never modulated, the session's by group, no `overlay.*` alias — and it
    is not a window-system setting: `apply` pushes nothing for it."""
    from hyperspace.params import part_of

    assert Output(None, None).dim == 1.0 and Output("win", FakeBackend(), allowed=True).dim == 1.0
    r, out = rig.reg, rig.out
    p = r["output.dim"]
    assert p.kind is Kind.CONTINUOUS and (p.lo, p.hi) == (0.0, 1.0) and p.value == 1.0
    assert not p.persist and not p.modulatable and not p.alias
    assert p.group == "output" and part_of(p) == "session"
    assert "overlay.dim" not in r
    assert "output.dim" not in r.snapshot("output") and "output.dim" not in r.snapshot()
    assert p.text() == "100%"
    p.set_norm(0.4)
    assert out.dim == pytest.approx(0.4) and p.text() == "40%"
    p.set_norm(0.0)
    assert out.dim == 0.0 and p.text() == "black"
    assert (p.fmt(0.996), p.fmt(0.004), p.fmt(1.0)) == ("99%", "1%", "100%")
    p.set(7.0)                                     # the setter holds the range
    assert out.dim == 1.0
    p.set(-3.0)
    assert out.dim == 0.0
    # the ground is its own thing: the dim never touches what the window clears to
    assert out.bg_alpha == 1.0
    out.apply()
    assert not any("dim" in str(c) for c in rig.b.calls)


def test_legacy_overlay_ids_are_views(rig):
    r = rig.reg
    for old, new in (("on", "overlay"), ("passthrough", "passthrough"), ("bg", "bg"),
                     ("alpha", "alpha"), ("monitor", "monitor")):
        p = r[f"overlay.{old}"]
        assert p.alias and not p.persist and not p.modulatable
        assert p.kind is r[f"output.{new}"].kind
    # a MIDI map bound to the old id moves the new param, and reads it back
    r["overlay.on"].toggle()
    assert rig.out.overlay is True and r["output.overlay"].base is True
    r["output.bg"].set_norm(0.5)
    assert r["overlay.bg"].norm == pytest.approx(0.5)
    assert r["overlay.monitor"].names == ["follow window", "Built-in", "Studio"]


# ---- state machine ----

def test_nothing_happens_until_apply(rig):
    rig.out.apply()
    assert ("spaces", True) not in rig.b.calls
    assert rig.b.calls == [("MOUSE_PASSTHROUGH", False), ("opacity", 1.0)]  # off: clickable


def test_fullscreen_is_glfws_own_on_the_windows_monitor(rig):
    rig.reg["output.fullscreen"].set(True)
    rig.out.apply()
    c = rig.b.calls
    assert ("fullscreen", "Built-in") in c
    assert rig.b.rect == (0, 0, 1728, 1117)
    # opaque and ordinary: no float, no see-through, clicks stay with us
    assert ("FLOATING", True) not in c and ("spaces", True) not in c
    assert ("MOUSE_PASSTHROUGH", True) not in c
    assert rig.out.mode == "fullscreen" and rig.out.bg_alpha == 1.0
    rig.b.calls.clear()
    rig.reg["output.fullscreen"].set(False)
    rig.out.apply()
    assert ("windowed", (100, 100, 1280, 820)) in rig.b.calls
    assert rig.b.rect == (100, 100, 1280, 820)


def test_overlay_covers_floats_and_clears(rig):
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    c = rig.b.calls
    assert ("DECORATED", False) in c and ("FLOATING", True) in c and ("spaces", True) in c
    assert not any(k == "fullscreen" for k, _ in c)
    assert rig.b.rect == (0, 0, 1728, 1117)
    assert rig.out.mode == "overlay" and rig.out.bg_alpha == 0.0


def test_leave_restores_everything(rig):
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    rig.b.calls.clear()
    rig.reg["output.overlay"].set(False)
    rig.out.apply()
    c = rig.b.calls
    assert ("spaces", False) in c and ("FLOATING", False) in c and ("DECORATED", True) in c
    assert rig.b.rect == (100, 100, 1280, 820)
    assert rig.out.mode == "window" and rig.out.bg_alpha == 1.0


def test_overlay_wins_and_mode_changes_go_through_the_plain_window(rig):
    rig.reg["output.fullscreen"].set(True)
    rig.out.apply()
    rig.b.calls.clear()
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    c = rig.b.calls
    # fullscreen left first (back to the saved rect), then the cover entered
    assert c.index(("windowed", (100, 100, 1280, 820))) < c.index(("DECORATED", False))
    assert ("FLOATING", True) in c and ("spaces", True) in c
    assert rig.b.rect == (0, 0, 1728, 1117)
    rig.b.calls.clear()
    # overlay off but fullscreen still on: the cover goes, GLFW fullscreen returns
    rig.reg["output.overlay"].set(False)
    rig.out.apply()
    c = rig.b.calls
    assert c.index(("DECORATED", True)) < c.index(("fullscreen", "Built-in"))
    assert rig.out.mode == "fullscreen" and rig.b.rect == (0, 0, 1728, 1117)
    rig.b.calls.clear()
    rig.reg["output.fullscreen"].set(False)
    rig.out.apply()
    assert rig.b.rect == (100, 100, 1280, 820)  # the original rect survived the trip


def test_passthrough_defaults_on_but_only_applies_in_overlay(rig):
    assert rig.out.passthrough is True
    rig.reg["output.fullscreen"].set(True)
    rig.out.apply()
    assert ("MOUSE_PASSTHROUGH", True) not in rig.b.calls
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    assert ("MOUSE_PASSTHROUGH", True) in rig.b.calls
    rig.b.calls.clear()
    rig.reg["output.overlay"].set(False)
    rig.out.apply()
    assert ("MOUSE_PASSTHROUGH", False) in rig.b.calls


def test_bg_and_alpha(rig):
    rig.reg["output.bg"].set_norm(0.5)
    rig.reg["output.alpha"].set_norm(0.25)
    rig.out.apply()
    assert rig.out.bg_alpha == 1.0  # off: opaque, opacity untouched
    assert ("opacity", 0.25) not in rig.b.calls
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    assert rig.out.bg_alpha == pytest.approx(0.5)
    assert ("opacity", 0.25) in rig.b.calls
    rig.b.calls.clear()
    rig.out.apply()
    assert rig.b.calls == []  # change-gated: a quiet frame sends nothing


def test_monitor_switch_while_on(rig):
    rig.reg["output.fullscreen"].set(True)
    rig.out.apply()
    rig.reg["output.monitor"].set(2)
    rig.out.apply()
    assert ("fullscreen", "Studio") in rig.b.calls
    assert rig.b.rect == (1728, 0, 2560, 1440)
    rig.b.calls.clear()
    # leaving puts the window back where it was, whichever screen it covered
    rig.reg["output.fullscreen"].set(False)
    rig.out.apply()
    assert rig.b.rect == (100, 100, 1280, 820)
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    assert rig.b.rect == (1728, 0, 2560, 1440)
    rig.reg["output.monitor"].set(1)
    rig.out.apply()
    assert rig.b.rect == (0, 0, 1728, 1117)


def test_monitor_chosen_beforehand_is_the_target(rig):
    rig.reg["output.monitor"].set(2)
    rig.out.apply()
    assert not any(k in ("rect", "fullscreen") for k, _ in rig.b.calls)  # a plain window stays put
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    assert rig.b.rect == (1728, 0, 2560, 1440)


def test_follow_window_is_the_first_choice_and_reads_back_as_itself(rig):
    """monitor −1 — the screen the window is on — is a choice of its own,
    not screen 0 (audit P3): the readout says so, and choosing a screen by
    name then going back to it covers the window's own screen again."""
    p = rig.reg["output.monitor"]
    assert rig.out.monitor == -1 and p.text() == "follow window"
    rig.b.rect = (1800, 100, 1280, 820)         # the window sits on Studio
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    assert rig.b.rect == (1728, 0, 2560, 1440)  # …so the overlay covers Studio
    p.set(1)                                    # Built-in, by name
    rig.out.apply()
    assert rig.out.monitor == 0 and rig.b.rect == (0, 0, 1728, 1117)
    p.set(0)                                    # back to following the window
    rig.out.apply()
    assert rig.out.monitor == -1 and p.text() == "follow window"
    assert rig.b.rect == (1728, 0, 2560, 1440)  # the saved rect is on Studio


def test_no_monitors_means_nothing_to_cover(rig):
    rig.b.mons = []
    rig.reg["output.fullscreen"].set(True)
    rig.out.apply()
    assert rig.b.rect == (100, 100, 1280, 820) and rig.out.error == ""
    assert rig.reg["output.monitor"].names == ["follow window"]


def test_backend_error_is_reported_not_raised(rig):
    def boom(*a):
        raise RuntimeError("no cocoa")

    rig.b.set_attrib = boom
    rig.reg["output.overlay"].set(True)
    rig.out.apply()
    assert rig.out.error.startswith("output: no cocoa")


def test_windowed_rect_is_the_saved_rect_while_fullscreen_or_overlay(rig):
    """What the launch placement remembers (plan 16 WP4, fork F6): the
    plain window's rect, never the cover of a screen — and reading it
    moves nothing."""
    home = (100, 100, 1280, 820)
    assert rig.out.windowed_rect() == home
    rig.b.rect = home = (240, 180, 1000, 700)            # dragged and resized
    assert rig.out.windowed_rect() == home
    for mode in ("fullscreen", "overlay"):
        # the toggle flipped but not yet applied: the window is still a window
        rig.reg[f"output.{mode}"].set(True)
        assert rig.out.windowed_rect() == home
        rig.out.apply()
        assert rig.b.rect == (0, 0, 1728, 1117)          # it covers the screen…
        assert rig.out.windowed_rect() == home           # …and is remembered by its window
        rig.reg["output.monitor"].set(2)                 # another screen while on: the same
        rig.out.apply()
        assert rig.b.rect == (1728, 0, 2560, 1440) and rig.out.windowed_rect() == home
        rig.reg["output.monitor"].set(0)
        rig.reg[f"output.{mode}"].set(False)
        rig.out.apply()
        assert rig.b.rect == home and rig.out.windowed_rect() == home
    # read-only: no window-system call, no state moved
    rig.reg["output.fullscreen"].set(True)
    rig.out.apply()
    calls, applied, saved = list(rig.b.calls), dict(rig.out._applied), rig.out._saved_rect
    rig.out.windowed_rect()
    assert (rig.b.calls, rig.out._applied, rig.out._saved_rect) == (calls, applied, saved)
    # no backend: nothing to say; a window system that raises: the same
    assert Output(None, None).windowed_rect() is None and Output("win", None).windowed_rect() is None
    out = Output("win", FakeBackend())
    out.backend.window_rect = lambda win: 1 / 0
    assert out.windowed_rect() is None


def test_headless_output_has_no_window_to_push_to():
    reg = _registry()
    out = Output(None, None, allowed=True)
    out.register(reg)
    reg["output.overlay"].toggle()
    out.apply()
    assert out.overlay is True and out.bg_alpha == 0.0
    assert reg["output.monitor"].names == ["follow window", "screen"]


# ---- decision 21 (a): overlay only when the config asks ----

@pytest.fixture()
def gated():
    """`[output] overlay = false`, the default: Output's own default too."""
    reg = _registry()
    b = FakeBackend()
    out = Output("win", b)
    out.register(reg)
    return SimpleNamespace(reg=reg, out=out, b=b)


def test_overlay_is_shut_by_default():
    assert Output(None, None).allowed is False


def test_overlay_refuses_every_road_while_the_config_shuts_it(gated):
    """The T key and the APC40's MASTER select are rows on `overlay.on`
    (the factory table, apc40.DEFAULT_MAP); the panel sets `output.overlay`;
    a preset restores values. Every one lands on the one param, and it
    stays off — the window never leaves window mode."""
    from hyperspace import apc40, routing

    r, out = gated.reg, gated.out
    t = next(b for b in routing.Bindings.factory().bindings
             if b.source == "key:T" and b.target == "overlay.on")
    master = next(d for d in apc40.DEFAULT_MAP if d["source"] == "note:0:80")
    assert master["target"] == "overlay.on"
    routing.act(r, t)                                         # T
    routing.act(r, routing.Binding.from_json(master))         # MASTER select
    r["output.overlay"].set(True)                             # the panel's toggle
    r["overlay.on"].toggle()
    r.restore({"output.overlay": True, "overlay.on": True})   # a preset naming it
    out.apply()
    assert out.overlay is False and out.mode == "window"
    assert r["output.overlay"].get() is False
    # the first apply settles the plain window: click-through off, opacity 1
    assert gated.b.calls == [("MOUSE_PASSTHROUGH", False), ("opacity", 1.0)]


def test_the_ground_and_opacity_do_nothing_while_shut(gated):
    """`overlay.bg` still lands a value, but the window
    clears opaque and its opacity is never touched."""
    gated.reg["overlay.bg"].set_norm(0.0)
    gated.reg["output.alpha"].set_norm(0.2)
    gated.out.overlay = True        # even a forced flag: mode reads the gate
    gated.out.apply()
    assert gated.out.bg_alpha == 1.0 and gated.out.mode == "window"
    assert [a for k, a in gated.b.calls if k == "opacity"] == [1.0]


def test_fullscreen_still_works_while_overlay_is_shut(gated):
    gated.reg["output.fullscreen"].set(True)
    gated.out.apply()
    assert gated.out.mode == "fullscreen" and ("fullscreen", "Built-in") in gated.b.calls


# ---- plan 21 WP4: the per-output switches ----

def _slots(*names, missing=()):
    from hyperspace.outputs import Slot, Switches

    return [Slot(k + 1, name=n, switches=Switches(),
                 win=None if k + 1 in missing else f"w{k + 1}") for k, n in enumerate(names)]


def test_the_output_switches_are_rig_settings():
    """Fork F4: output.N.scene / .hands / .through / .dim are rig settings —
    group `output` (the session's), never persisted (no preset, show or
    undo step holds them: `undo.watched` needs persist), not modulatable
    (no lane rides them) — and they write the output's `Switches`, which
    the renderer reads. Generated for the outputs that opened, numbered by
    their place in the config's list; labels name the output when there
    are several."""
    from hyperspace import undo
    from hyperspace.overlay import register_switches
    from hyperspace.params import part_of

    reg = _registry()
    slots = _slots("glass", "projector", "wall", missing=(2,))
    ids = register_switches(reg, slots)
    assert ids == ["output.1.scene", "output.1.hands", "output.1.through", "output.1.dim",
                   "output.3.scene", "output.3.hands", "output.3.through", "output.3.dim"]
    assert not any(p.id.startswith("output.2.") for p in reg)       # not opened: none
    for pid in ids:
        p = reg[pid]
        assert p.group == "output" and part_of(p) == "session"
        assert not p.persist and not p.modulatable and not p.alias and not undo.watched(p)
    assert not any(pid in reg.snapshot() for pid in ids)
    assert not any(pid in reg.snapshot(part="session") for pid in ids)
    assert reg["output.1.scene"].kind is Kind.TOGGLE and reg["output.1.dim"].kind is Kind.CONTINUOUS
    assert reg["output.1.scene"].label == "Glass scene"
    assert reg["output.3.through"].label == "Wall hands through effects"
    # they write the Switches the app hands the renderer
    sw = slots[2].switches
    reg["output.3.scene"].set(False)
    reg["output.3.through"].set(True)
    reg["output.3.dim"].set(0.25)
    assert (sw.scene, sw.hands, sw.through, sw.dim) == (False, True, True, 0.25)
    reg["output.3.dim"].set(4.0)
    assert sw.dim == 1.0 and reg["output.3.dim"].text() == "100%"
    reg["output.3.dim"].set(0.0)
    assert sw.dim == 0.0 and reg["output.3.dim"].text() == "black"
    # the launch values are the slot's (the config's) as the params find them
    from hyperspace.outputs import Slot, Switches

    seeded = Slot(1, win="w", switches=Switches(scene=False, dim=0.4))
    reg2 = _registry()
    register_switches(reg2, [seeded, *_slots("x", "y")[1:]])
    assert reg2["output.1.scene"].value is False and reg2["output.1.dim"].value == 0.4


def test_one_output_has_no_dim_of_its_own():
    """With one output the master dim is that output's dim (§3 budget):
    three switches, plainly labelled, no output.1.dim."""
    from hyperspace.overlay import register_switches

    reg = _registry()
    assert register_switches(reg, _slots("")) == [
        "output.1.scene", "output.1.hands", "output.1.through"]
    assert "output.1.dim" not in reg
    assert [reg[f"output.1.{k}"].label for k in ("scene", "hands", "through")] == [
        "Scene", "Hands", "Hands through effects"]
