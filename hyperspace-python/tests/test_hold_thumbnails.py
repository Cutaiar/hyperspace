"""Plans 37 and 38 together (the integration seam, B3's I2): the GRAPH
page's thumbnails come from the renderer the canvas reads
(`hold.canvas_renderer`), through `ui_graph.picture_sources`.

While the projector is held and the preview has been drawn, the page wants
its nodes from the preview renderer's own `PreviewTextures` and the main
renderer copies none; after Take or Drop they go back to the main one; a
hold with the page closed makes no thumbnail at all. Output 1's thumbnail
while held is the program's picture (`panel.monitor`, the PROJECTOR
inset's), never the preview's."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from conftest import seed
from test_graph_legible import party as _party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import hold as H
from hyperspace import ui_graph
from hyperspace.outputs import Preview, PreviewTextures

# ---------------------------------------------------------------- headless

def party(rig):
    """`test_graph_legible.party` over the corpus: party-trip is test data
    since 2026-10-28, seeded into the rig's home first (never over a file)."""
    seed(rig.lib.home, "presets")
    return _party(rig)


def _hold(on: bool, preview=None):
    return NS(on=on, preview=preview, since=0.0, error="", changed=list,
              rewired=lambda: False, engage=lambda t: None, take=lambda: True,
              drop=lambda: True)


def test_the_picture_sources_follow_the_canvas_renderer():
    main_th, pv_th = PreviewTextures(None), PreviewTextures(None)
    main = NS(_graph="held", thumbs=main_th, stats={"gpu_ms": {"scene": 2.0}})
    pr = NS(_graph=None, thumbs=pv_th, stats={"gpu_ms": {"scene": 0.5}})
    hold = _hold(False, pr)
    panel = NS(renderer=main, hold=hold, preview=Preview(), monitor=Preview())
    assert ui_graph.picture_sources(panel) == (main_th, panel.preview, {"scene": 2.0})
    hold.on = True                      # held, the preview not drawn yet: the main one's
    th, pv, gpu = ui_graph.picture_sources(panel)
    assert th is main_th and pv is panel.monitor and gpu == {"scene": 2.0}
    pr._graph = "edited"                # drawn once: the preview's
    th, pv, gpu = ui_graph.picture_sources(panel)
    assert th is pv_th and pv is panel.monitor and gpu == {"scene": 0.5}
    hold.on = False                     # Take or Drop: the main one's again
    assert ui_graph.picture_sources(panel) == (main_th, panel.preview, {"scene": 2.0})
    # a panel with no hold (a test's) reads its renderer and its preview
    bare = NS(renderer=main, preview=panel.preview)
    assert ui_graph.picture_sources(bare) == (main_th, panel.preview, {"scene": 2.0})
    # the SYSTEM line counts the thumbnails the canvas reads
    hold.on = True
    pv_th.count, pv_th.repainted = 3, 1
    assert ui_graph.thumbnail_line(panel).startswith("thumbnails · 3 copied · 1 repainted")


def test_the_main_renderers_thumbnails_are_never_handed_to_the_preview():
    assert "thumbs" not in H.MIRRORED
    main = NS(thumbs=PreviewTextures(None), ghost=None, **{n: None for n in H.MIRRORED})
    pr = NS(thumbs=PreviewTextures(None), ghost=None)
    H.mirror(main, pr)
    assert pr.thumbs is not main.thumbs


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def test_held_the_page_wants_from_the_previews_thumbnails(rig):
    """Headless draw of the page while held: the wishes land on the
    preview renderer's `PreviewTextures`, none on the main one's; output 1's
    picture asked for is the monitor's (the program's)."""
    st = party(rig)
    g = rig.panel.renderer._graph
    main_th, pv_th = PreviewTextures(None), PreviewTextures(None)
    rig.panel.renderer = NS(_graph=g, thumbs=main_th, stats={})
    rig.panel.hold = _hold(True, NS(_graph=g, thumbs=pv_th, stats={}))
    rig.panel.preview, rig.panel.monitor = Preview(), Preview()
    st["preset_only"], st["pan"] = False, (-1600.0, 0.0)    # the scene's column on screen
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    assert st["thumbs"] is pv_th and st["preview"] is rig.panel.monitor
    assert pv_th.wanted and not main_th.wanted
    rig.panel.hold.on = False           # Take: the main one's again
    frame(rig.panel, "graph")
    assert main_th.wanted and ui_graph._state(rig.panel)["preview"] is rig.panel.preview


# ---------------------------------------------------------------- on GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def _setup(ctx):
    from test_outputs import H as HH
    from test_outputs import W, fbo, scene_view

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.graphmigrate import wiring_of
    from hyperspace.outputs import Switches, View
    from hyperspace.params import build_registry
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.wiring = wiring_of(r.fx.state)
    s = scene_view()
    chain = Analyzer(Analyser())
    reg = build_registry(s, Control(chain), NS(chain=chain), None,
                         dream=r.lookback.state, fx=r.fx.state)
    hold = H.Hold(reg, r, make=lambda: H.preview_renderer(r))
    panel = NS(renderer=r, hold=hold, preview=Preview(), monitor=Preview())
    out, pv = fbo(ctx), fbo(ctx)

    def step(page: bool, t: float = 2.0):
        """One app frame: the page (when drawn) wants the scene's thumbnail
        from the renderer the canvas reads; the outputs (the program while
        held); the preview after them while held and the page drawn."""
        if page:
            th, _, _ = ui_graph.picture_sources(panel)
            th.want({"scene": "picture"})
        if hold.on:
            with hold.program():
                r.draw_outputs(s, W, HH, 1.0, [View(Switches(), (W, HH), target=out)], t_now=t)
            if page:
                assert hold.draw_preview(s, W, HH, (W, HH), pv,
                                         lambda sz, f: View(Switches(), sz, target=f))
        else:
            r.draw_outputs(s, W, HH, 1.0, [View(Switches(), (W, HH), target=out)], t_now=t)

    return r, hold, panel, step


def test_on_gl_held_the_preview_renderer_makes_the_thumbnails_and_the_main_none(ctx):
    r, hold, panel, step = _setup(ctx)
    step(True)
    assert r.thumbs.count == 1 and "scene" in r.thumbs.tex
    hold.engage()
    step(True)              # the first held frame: the preview not drawn before it
    pr = hold.preview
    assert pr is not None and pr.thumbs is not None and pr.thumbs is not r.thumbs
    for _ in range(2):
        step(True)
        assert pr.thumbs.count == 1 and "scene" in pr.thumbs.tex
        assert r.thumbs.count == 0
    assert ui_graph.picture_sources(panel)[0] is pr.thumbs
    assert hold.take()
    step(True)
    step(True)
    assert r.thumbs.count == 1 and not pr.thumbs.wanted     # (the preview not drawn: nothing asked of it)
    assert ui_graph.picture_sources(panel)[0] is r.thumbs
    # and once more, left by Drop
    hold.engage()
    step(True)
    step(True)
    assert pr.thumbs.count == 1 and r.thumbs.count == 0
    assert hold.drop()
    step(True)
    step(True)
    assert r.thumbs.count == 1 and not pr.thumbs.wanted     # (the preview not drawn: nothing asked of it)
    assert ctx.error == "GL_NO_ERROR"


def test_on_gl_a_hold_with_the_page_closed_makes_no_thumbnail(ctx):
    r, hold, _, step = _setup(ctx)
    hold.engage()
    for k in range(3):
        step(False, 2.0 + k / 60)
    assert r.thumbs.count == 0 and not r.thumbs.tex
    assert hold.preview is None             # no preview renderer, so none of its thumbnails
    assert ctx.error == "GL_NO_ERROR"
