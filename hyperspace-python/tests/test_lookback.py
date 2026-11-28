"""What survives of the look-back's tests: the render window's
opaque ground through every corpus loadable patch, and the
dream layer menu's words.

The look-back and the old dream node are retired: the
dream is the effect file `dream` (tests/test_dream_effect.py), a saved one
opens as its parts (tests/test_dream_migration.py), and the legacy unit
converters in `hyperspace/lookback.py` are tested in tests/test_loadable.py.

Everything runs offscreen on a standalone GL context (skipped where there
is none).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import CORPUS, seed

moderngl = pytest.importorskip("moderngl")

from hyperspace.overlay import Output
from hyperspace.render import Renderer
from hyperspace.view import ViewState

VIEW = {"ang": [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], "yaw": 0.4, "pitch": 0.25}


class Rig:
    """A renderer on an RGBA texture target of size (w, h), read back as arrays."""

    def __init__(self, ctx, w, h, bg_alpha=1.0):
        self.ctx, self.w, self.h = ctx, w, h
        self.tex = ctx.texture((w, h), 4)
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.r = Renderer(ctx)
        self.r.bg_alpha = bg_alpha
        self.s = ViewState(shape=3, ang=list(VIEW["ang"]), yaw=VIEW["yaw"], pitch=VIEW["pitch"])

    def frame(self, t=0.0):
        self.fbo.use()
        self.ctx.viewport = (0, 0, self.w, self.h)
        self.r.draw(self.s, self.w, self.h, t_now=t)
        self.s.ang[3] += 0.03

    def read(self):
        return np.frombuffer(self.fbo.read(components=4), dtype=np.uint8).reshape(
            self.h, self.w, 4).copy()

    def scene(self):
        """The scene texture as the post pass sees it."""
        return np.frombuffer(self.r.scene.fbo.read(components=4), dtype=np.uint8).reshape(
            self.h, self.w, 4).copy()

    def release(self):
        self.fbo.release()
        self.tex.release()


# ---------------------------------------------------------------- the opaque ground

def test_cut_through_never_cuts_an_opaque_ground(ctx):
    """On an opaque ground — window
    and fullscreen — faces leave every pixel at alpha 255 whether
    cut-through is on (the default) or off; the fills still draw."""
    rig = Rig(ctx, 256, 256, bg_alpha=Output(None, None).bg_alpha)   # window mode: 1
    rig.s.faces, rig.s.lines, rig.s.points = True, True, False
    assert rig.s.cut_through
    for cut in (True, False):
        rig.s.cut_through = cut
        rig.frame()
        out = rig.read()
        assert (out[..., 3] == 255).all(), f"cut_through={cut} let the desktop through"
        assert out[..., :3].max() > 0, "the fills must still draw"
    rig.release()


def test_cut_through_still_cuts_in_overlay_mode(ctx):
    """Overlay mode's see-through ground: cut-through on lets the fills
    lower the window's alpha below the ground's; off, alpha composites over
    the ground and never drops below it."""
    out_ = Output(None, None, allowed=True)   # [output] overlay = true
    out_.overlay, out_.bg = True, 0.6
    rig = Rig(ctx, 256, 256, bg_alpha=out_.bg_alpha)
    ground = round(0.6 * 255)
    rig.s.faces, rig.s.lines, rig.s.points = True, False, False
    rig.s.cut_through = True
    rig.frame()
    assert rig.read()[..., 3].min() < ground - 2, "in overlay the fills must cut the alpha"
    rig.s.cut_through = False
    rig.frame()
    out = rig.read()
    assert out[..., 3].min() >= ground - 1
    assert out[..., :3].max() > 0
    rig.release()


def _preset_rig(ctx, tmp_path):
    """The app's construction order (tests/test_loadable.py `boot`), the
    renderer's own fx state on the registry."""
    from hyperspace import lfo, tempo
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.loadable import LoadedPatch
    from hyperspace.params import build_registry
    from hyperspace.routing import Bindings, Router

    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    r = Renderer(ctx)
    seed(tmp_path)                   # (the corpus: the loadable patches the build once shipped)
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.install,
                         fx=r.fx.state)
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    lib.attach(reg)
    router = Router(reg, Bindings())
    loaded_patch = LoadedPatch(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, view=view, r=r, loaded_patch=loaded_patch)


def _final_alpha(ctx, b, bg_alpha, w=240, h=160, frames=4):
    tex = ctx.texture((w, h), 4)
    fbo = ctx.framebuffer(color_attachments=[tex])
    b.r.bg_alpha = bg_alpha
    for k in range(frames):
        b.reg.apply()
        b.view.integrate(1 / 60)
        fbo.use()
        ctx.viewport = (0, 0, w, h)
        b.r.draw(b.view, w, h, t_now=k / 60)
    a = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(h, w, 4)[..., 3].copy()
    fbo.release()
    tex.release()
    return a


def _corpus_loadables():
    """The loadable patches the build once shipped (tests/corpus/loadable), by slug."""
    return sorted(p.stem for p in (CORPUS / "loadable").glob("*.json"))


# every effect on at its own blend, then every one forced to multiply
# (a × b drops alpha wherever an effect returns less than 1)
STRESS = ["effects", "multiply"]


@pytest.mark.parametrize("name", _corpus_loadables() + STRESS)
def test_every_corpus_loadable_renders_opaque_in_window_mode(ctx, tmp_path, name):
    """The render window is a Pepper's Ghost screen — in window
    mode (and fullscreen, the same opaque ground) every pixel of the final
    frame is alpha 255 for every corpus loadable patch, and for a loadable patch with
    cut-through, faces, points and every effect on, through the FX chain
    (the look-back is retired: a saved one is its parts)."""
    b = _preset_rig(ctx, tmp_path)
    first = _corpus_loadables()[0] if name in STRESS else name
    path = b.lib.path_of("loadable", first)
    assert path is not None, first
    b.loaded_patch.load(json.loads(path.read_text())["name"])
    assert b.lib.current("loadable") is not None
    if name in STRESS:
        # (every effect file exists for the stress — `FxState.hold(None)`)
        from hyperspace.fx import declare

        declare(b.reg, b.r.fx.state, b.r.fx.state.hold(None))
        values = {"view.faces": True, "view.cut_through": True, "view.lines": True,
                  "view.points": True, "fx.on": True, "fx.mix": 1.0}
        for fx_name in b.r.fx.state.specs:
            values[f"fx.{fx_name}.on"] = True
            values[f"fx.{fx_name}.mix"] = 1.0
        assert b.reg.restore(values) == []
        # every effect in the run, as a load of these values lands it
        from hyperspace.graphmigrate import wiring_of
        b.r.wiring = wiring_of(b.r.fx.state)
        if name == "multiply":
            for fx_name in b.r.fx.state.specs:
                b.reg[f"fx.{fx_name}.blend"].set(3)
    a = _final_alpha(ctx, b, Output(None, None).bg_alpha)
    assert (a == 255).all(), f"{name}: {(a < 255).mean():.1%} below 255, lowest {a.min()}"
    if name in STRESS:
        assert b.r.stats["fx_on"] and b.view.cut_through and b.view.faces


# ---------------------------------------------------------------- the dream layer menu

def test_every_layer_has_its_words():
    """Each name in LAYERS is in LAYER_INFO once (and nothing else is),
    with a net, a short line that fits the closed menu beside the name and
    a longer one; the menu is grouped by net, VGG16 first."""
    from hyperspace.dreamhook import LAYER_INFO, LAYERS

    assert len(LAYERS) == len(set(LAYERS)) == 25
    assert set(LAYER_INFO) == set(LAYERS)
    nets = [net for net, _, _ in LAYER_INFO.values()]
    assert nets == ["VGG16"] * 13 + ["GoogLeNet"] * 12
    for name, (_, short, long) in LAYER_INFO.items():
        assert short and len(short) <= 26 and "\n" not in short, name
        assert len(long) > len(short) and long.endswith("."), name
        assert ("slower" in short) == ("Slower" in long), name

